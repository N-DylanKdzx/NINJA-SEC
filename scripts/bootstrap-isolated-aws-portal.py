"""Seed and verify the disposable AWS portal using a temporary VPC Lambda."""

import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import re
import secrets
import ssl
import subprocess
import time
import urllib.request
import zipfile

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


PROBE_CODE = """
import http.client
import json
import pathlib
import socket
import ssl
import uuid
from http.cookies import SimpleCookie

import pymysql


def seed(event):
    context = ssl.create_default_context(cafile='/var/task/rds-ca.pem')
    runtime = event['runtime']
    master = event['master']
    with pymysql.connect(host=event['database'], user=master['username'], password=master['password'],
                         autocommit=True, ssl=context, connect_timeout=5) as conn, conn.cursor() as cur:
        cur.execute("SELECT @@require_secure_transport")
        if not cur.fetchone()[0]:
            raise RuntimeError('Database does not enforce TLS')
        cur.execute('CREATE DATABASE IF NOT EXISTS ninjasec')
        cur.execute('CREATE DATABASE IF NOT EXISTS ninjasec_auth')
        cur.execute('USE ninjasec')
        cur.execute(pathlib.Path('/var/task/schema.sql').read_text())
        cur.execute('''CREATE TABLE IF NOT EXISTS ninjasec_auth.portal_sessions (
            token_hash BINARY(32) PRIMARY KEY,
            expires_at DATETIME NOT NULL,
            INDEX session_expiry (expires_at)
        ) ENGINE=InnoDB''')
        cur.execute("CREATE USER IF NOT EXISTS 'portal_replay'@'%%' IDENTIFIED BY %s REQUIRE SSL",
                    (runtime['password'],))
        cur.execute("ALTER USER 'portal_replay'@'%%' IDENTIFIED BY %s REQUIRE SSL",
                    (runtime['password'],))
        cur.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ninjasec.incidents TO 'portal_replay'@'%'")
        cur.execute("GRANT SELECT, INSERT, DELETE ON ninjasec_auth.portal_sessions TO 'portal_replay'@'%'")
        cur.execute("SHOW SESSION STATUS LIKE 'Ssl_version'")
        return {'database_tls': cur.fetchone()[1]}


class InternalHTTPS(http.client.HTTPSConnection):
    def __init__(self, hostname, destination):
        super().__init__(hostname, timeout=12, context=ssl.create_default_context())
        self.destination = destination

    def connect(self):
        raw = socket.create_connection((self.destination, 443), timeout=self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except Exception:
            raw.close()
            raise


def verify(event):
    session_cookie = None
    def request(method, path, expected, body=None):
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'NINJA-SEC-IaC-Verification/1.0',
            'X-NINJASEC-Action': '1',
        }
        if session_cookie:
            headers['Cookie'] = session_cookie
        conn = InternalHTTPS(event['hostname'], event['alb_dns'])
        try:
            conn.request(method, path, json.dumps(body) if body is not None else None, headers)
            response = conn.getresponse()
            payload = response.read()
            if response.status != expected:
                raise RuntimeError(f'{method} {path}: expected {expected}, got {response.status}')
            return payload, response.getheader('Set-Cookie')
        finally:
            conn.close()

    request('GET', '/health', 200)
    runtime = event['runtime']
    _, cookie_header = request('POST', '/auth/login', 204, {
        'username': runtime['portal_user'], 'password': runtime['portal_password']})
    cookie = next(iter(SimpleCookie(cookie_header).values()))
    if not cookie['secure'] or not cookie['httponly'] or cookie['samesite'].lower() != 'strict':
        raise RuntimeError('Unexpected session cookie settings')
    session_cookie = f'{cookie.key}={cookie.value}'
    title = f'IaC replay {uuid.uuid4()}'
    body = {'title': title, 'description': 'Synthetic verification', 'status': 'abierto'}
    raw, _ = request('POST', '/api/incidents', 201, body)
    item = json.loads(raw)
    path = f"/api/incidents/{int(item['id'])}"
    try:
        raw, _ = request('GET', '/api/incidents', 200)
        if not any(row['id'] == item['id'] and row['title'] == title for row in json.loads(raw)):
            raise RuntimeError('Created incident not returned by GET')
        body['status'] = 'resuelto'
        raw, _ = request('PUT', path, 200, body)
        if json.loads(raw)['status'] != 'resuelto':
            raise RuntimeError('Update not reflected')
    finally:
        request('DELETE', path, 204)
    request('POST', '/auth/logout', 204)
    request('GET', '/api/incidents', 401)
    return {'login': 204, 'create': 201, 'read': 200, 'update': 200, 'delete': 204, 'logout': 204}


def run(event, context):
    return seed(event) if event['mode'] == 'seed' else verify(event)
"""


def probe_archive(region):
    context = ssl.create_default_context(cafile=os.getenv("AWS_CA_BUNDLE"))
    def download(url):
        with urllib.request.urlopen(url, context=context, timeout=30) as response:
            return response.read()
    metadata = json.loads(download("https://pypi.org/pypi/PyMySQL/1.2.4/json"))
    wheel = next(item for item in metadata["urls"] if item["filename"].endswith(".whl"))
    wheel_bytes = download(wheel["url"])
    if hashlib.sha256(wheel_bytes).hexdigest() != wheel["digests"]["sha256"]:
        raise ValueError("PyMySQL wheel hash mismatch")
    schema = Path(__file__).resolve().parents[1] / "portal" / "schema.sql"
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as dest:
        dest.writestr("probe.py", PROBE_CODE)
        dest.write(schema, "schema.sql")
        dest.writestr("rds-ca.pem", download(
            f"https://truststore.pki.rds.amazonaws.com/{region}/{region}-bundle.pem"))
        with zipfile.ZipFile(io.BytesIO(wheel_bytes)) as source:
            for name in source.namelist():
                if name.startswith("pymysql/") and not name.endswith("/"):
                    dest.writestr(name, source.read(name))
    return output.getvalue()


def read_outputs(args):
    process = subprocess.run(
        [args.terraform, f"-chdir={args.root}", "output", "-json"],
        capture_output=True, check=True,
    )
    result = json.loads(process.stdout)
    return result["service_demo"]["value"], result["portal_replay"]["value"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--terraform", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--role-arn", required=True)
    parser.add_argument("--hostname", required=True)
    parser.add_argument("--phase", choices=["seed", "verify"], required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9.-]+", args.hostname):
        parser.error("Use the DNS hostname on the ACM certificate")
    base, portal = read_outputs(args)
    session = boto3.Session(region_name="us-east-1")
    cfg = Config(read_timeout=65)
    account = session.client("sts").get_caller_identity()["Account"]
    if account != "533267256700" or not args.role_arn.startswith(f"arn:aws:iam::{account}:role/"):
        raise ValueError("Unexpected AWS account or Lambda role")
    name = "ninjasec-iac-service-demo"
    db = session.client("rds").describe_db_instances(DBInstanceIdentifier=name)["DBInstances"][0]
    if (base["rds_arn"] != db["DBInstanceArn"] or db["PubliclyAccessible"]
            or portal["vpc_id"] != db["DBSubnetGroup"]["VpcId"]
            or portal["database_host"] != db["Endpoint"]["Address"]):
        raise ValueError("Terraform outputs do not match the isolated private RDS")
    secrets_client = session.client("secretsmanager")
    secret_arn = portal["portal_secret_arn"]
    if secrets_client.describe_secret(SecretId=secret_arn)["Name"] != f"{name}/portal-runtime":
        raise ValueError("Unexpected portal secret")
    try:
        runtime = json.loads(secrets_client.get_secret_value(SecretId=secret_arn)["SecretString"])
    except ClientError as error:
        if args.phase != "seed" or error.response["Error"]["Code"] != "ResourceNotFoundException":
            raise
        runtime = {
            "username": "portal_replay",
            "password": secrets.token_hex(32),
            "portal_user": "operador",
            "portal_password": secrets.token_hex(32),
        }
    event = {"mode": args.phase, "runtime": runtime}
    if args.phase == "seed":
        event.update(
            database=portal["database_host"],
            master=json.loads(secrets_client.get_secret_value(
                SecretId=db["MasterUserSecret"]["SecretArn"])["SecretString"]),
        )
    else:
        targets = session.client("elbv2").describe_target_health(
            TargetGroupArn=base["target_group_arn"])["TargetHealthDescriptions"]
        if len(targets) != 2 or any(t["TargetHealth"]["State"] != "healthy" for t in targets):
            raise RuntimeError("Wait for both portal targets to become healthy")
        event.update(hostname=args.hostname, alb_dns=base["alb_dns"])
    client = session.client("lambda", config=cfg)
    function = f"ninjasec-portal-replay-{args.phase}-{secrets.token_hex(4)}"
    client.create_function(
        FunctionName=function, Runtime="python3.12", Handler="probe.run",
        Role=args.role_arn, Timeout=55, Code={"ZipFile": probe_archive(session.region_name)},
        VpcConfig={"SubnetIds": portal["app_subnet_ids"], "SecurityGroupIds": [portal["app_security_group"]]},
        Tags={"Project": "NINJA-SEC", "Purpose": "Isolated portal replay"},
    )
    print("TEMPORARY_PROBE", function, flush=True)
    try:
        client.get_waiter("function_active_v2").wait(
            FunctionName=function, WaiterConfig={"Delay": 5, "MaxAttempts": 120})
        response = client.invoke(FunctionName=function, Payload=json.dumps(event).encode())
        payload = json.load(response["Payload"])
        request_id = response["ResponseMetadata"]["RequestId"]
        if response.get("FunctionError"):
            raise RuntimeError(f"Portal {args.phase} probe failed ({request_id}, {payload.get('errorType')})")
        if args.phase == "seed":
            secrets_client.put_secret_value(SecretId=secret_arn, SecretString=json.dumps(runtime))
        print("PORTAL_REPLAY", args.phase, json.dumps(payload), request_id, flush=True)
    finally:
        client.delete_function(FunctionName=function)
        print("TEMPORARY_PROBE_REMOVED", function, flush=True)


if __name__ == "__main__":
    main()
