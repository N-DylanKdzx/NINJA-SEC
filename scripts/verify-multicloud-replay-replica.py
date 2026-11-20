"""Initialize and query the isolated OCI replica through a private Bastion session."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import ssl
import subprocess
import sys
import time
import uuid

import oci
import pymysql


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["initialize", "present", "absent"])
    args = parser.parse_args()
    state = json.load(sys.stdin)
    wireguard = state["wireguard"]["value"]
    target = state["oci_replay"]["value"]
    group = state["audit_replay"]["value"]["resource_group"]
    match = re.fullmatch(r"rg-ninjasec-audit-replay-([a-z0-9]{8,12})", group)
    if not match:
        raise ValueError("Expected the isolated replay resource group")
    name = f"ninjasec-m105-{match[1]}"
    cfg = oci.config.from_file(profile_name="NINJA_SEC_TERRAFORM")
    cfg["region"] = "us-ashburn-1"
    opts = {"timeout": (5, 25)}
    network = oci.core.VirtualNetworkClient(cfg, **opts)
    db = oci.mysql.DbSystemClient(cfg, **opts).get_db_system(target["database_id"]).data
    subnet = network.get_subnet(db.subnet_id).data
    client = oci.bastion.BastionClient(cfg, **opts)
    bastion = client.get_bastion(wireguard["oci_bastion"]).data
    if (db.display_name != f"{name}-mysql-private" or db.shape_name != "MySQL.2" or db.lifecycle_state != "ACTIVE"
            or db.ip_address != "10.244.11.10" or subnet.vcn_id != target["vcn_id"]
            or subnet.cidr_block != "10.244.11.0/24" or not subnet.prohibit_public_ip_on_vnic
            or bastion.name != name or bastion.target_subnet_id != target["subnets"]["private"]):
        raise ValueError("Bastion and database must belong to the isolated replay")

    home = Path.home() / ".ssh"
    key = home / "ninjasec_oci_bastion_rsa"
    known_hosts = home / "ninjasec_oci_known_hosts"
    public_key = subprocess.check_output(["ssh-keygen", "-y", "-f", str(key)], text=True).strip()
    session = client.create_session(oci.bastion.models.CreateSessionDetails(
        bastion_id=bastion.id, display_name=f"{name}-mysql",
        session_ttl_in_seconds=1800,
        key_details=oci.bastion.models.PublicKeyDetails(public_key_content=public_key),
        target_resource_details=oci.bastion.models.CreatePortForwardingSessionTargetResourceDetails(
            target_resource_private_ip_address=db.ip_address, target_resource_port=3306),
    )).data
    tunnel = None
    try:
        for _ in range(45):
            state = client.get_session(session.id).data.lifecycle_state
            if state == "ACTIVE":
                break
            if state in {"FAILED", "DELETED"}:
                raise RuntimeError("The isolated database Bastion session failed")
            time.sleep(4)
        else:
            raise RuntimeError("The isolated database Bastion session did not activate")
        time.sleep(8)
        with socket.socket() as port_socket:
            port_socket.bind(("127.0.0.1", 0))
            port = port_socket.getsockname()[1]
        tunnel = subprocess.Popen([
            "ssh", "-N", "-i", str(key), "-o", "BatchMode=yes", "-o", "ExitOnForwardFailure=yes",
            "-o", "StrictHostKeyChecking=accept-new", "-o", f"UserKnownHostsFile={known_hosts}",
            "-o", "ConnectTimeout=20", "-L", f"127.0.0.1:{port}:{db.ip_address}:3306",
            f"{session.id}@host.bastion.us-ashburn-1.oci.oraclecloud.com",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        for _ in range(30):
            if tunnel.poll() is not None:
                raise RuntimeError("SSH forwarding failed")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=1):
                    break
            except OSError:
                time.sleep(1)
        else:
            raise RuntimeError("SSH forwarding did not listen")

        # Pin the certificate presented by the private endpoint selected through the OCI control plane.
        openssl = Path(r"C:\Program Files\Git\usr\bin\openssl.exe")
        result = subprocess.run([
            str(openssl) if openssl.is_file() else "openssl", "s_client", "-starttls", "mysql",
            "-connect", f"127.0.0.1:{port}", "-showcerts",
        ], input=b"", capture_output=True, timeout=25)
        certificate = re.search(rb"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----",
                                result.stdout, re.DOTALL)
        if not certificate:
            raise RuntimeError("The isolated OCI database did not present a TLS certificate")
        pem = certificate[0].decode("ascii")
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        tls.check_hostname = False
        tls.verify_flags |= ssl.VERIFY_X509_PARTIAL_CHAIN
        tls.load_verify_locations(cadata=pem)
        password = os.environ["TF_VAR_oci_mysql_admin_password"]
        with pymysql.connect(host="127.0.0.1", port=port, user="ninjaadmin", password=password,
                             ssl=tls, connect_timeout=10, read_timeout=15, autocommit=True) as conn, conn.cursor() as cursor:
            if args.phase == "initialize":
                cursor.execute("SELECT @@lower_case_table_names, @@version")
                settings = cursor.fetchone()
                if settings[0] != 0:
                    raise RuntimeError("OCI case handling differs from the isolated RDS deployment")
                cursor.execute("CREATE DATABASE IF NOT EXISTS ninjasec")
                cursor.execute("USE ninjasec")
                schema = Path(__file__).resolve().parents[1] / "portal" / "schema.sql"
                cursor.execute(schema.read_text(encoding="utf-8"))
                print("M105_OCI_SCHEMA", db.id, settings[1], "TLS_CERT_SHA256",
                      hashlib.sha256(ssl.PEM_cert_to_DER_cert(pem)).hexdigest(), flush=True)
                return
            marker = str(uuid.UUID(os.environ["NINJASEC_REPLAY_MARKER"]))
            cursor.execute("USE ninjasec")
            expected = args.phase == "present"
            for _ in range(120):
                cursor.execute("SELECT id FROM incidents WHERE title=%s AND description=%s",
                               (f"NINJA-SEC M10.5 {marker}", marker))
                row = cursor.fetchone()
                if bool(row) == expected:
                    print("M105_OCI_REPLICA", args.phase, marker, row[0] if row else None, flush=True)
                    return
                time.sleep(2)
            raise RuntimeError(f"Replication marker failed the {args.phase} check")
    finally:
        if tunnel is not None and tunnel.poll() is None:
            tunnel.terminate()
            tunnel.wait(10)
        client.delete_session(session.id)


if __name__ == "__main__":
    main()
