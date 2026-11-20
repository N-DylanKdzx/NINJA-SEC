"""Verify an isolated Azure audit runbook with a synthetic record or a real S3 batch."""

import argparse
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid


def find_replay_cloudtrail_batch(vpc_id, suffix):
    import boto3
    from read_cloudtrail import canonical_bytes, read_batch

    session = boto3.Session(region_name="us-east-1")
    account = session.client("sts").get_caller_identity()["Account"]
    if account != "533267256700":
        raise ValueError("Unexpected AWS account for the audit check")
    [vpc] = session.client("ec2").describe_vpcs(VpcIds=[vpc_id])["Vpcs"]
    if (vpc["CidrBlock"] != "10.243.0.0/16"
            or {t["Key"]: t["Value"] for t in vpc.get("Tags", [])}.get("Name") != "ninjasec-iac-service-demo"):
        raise ValueError("Unexpected VPC for the isolated audit check")
    s3 = session.client("s3")
    bucket = f"ninjasec-audit-{account}"
    cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
    seen = set()
    for attempt in range(45):
        today = datetime.now(timezone.utc)
        for date in {today, today - timedelta(days=1)}:
            prefix = f"AWSLogs/{account}/CloudTrail/us-east-1/{date:%Y/%m/%d}/"
            for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
                for item in page.get("Contents", []):
                    key = item["Key"]
                    if key in seen or item["LastModified"] < cutoff or not key.endswith(".json.gz"):
                        continue
                    seen.add(key)
                    batch = read_batch(s3, bucket, [key])
                    for record in batch["Records"]:
                        response = record.get("responseElements") or {}
                        if (record.get("eventName") == "CreateVpc"
                                and (response.get("vpc") or {}).get("vpcId") == vpc_id):
                            batch["Records"] = [record]
                            print("M105_CLOUDTRAIL_EVENT", suffix, vpc_id, record["eventID"], key, flush=True)
                            return canonical_bytes(batch)
        if attempt % 5 == 0:
            print("M105_WAITING_FOR_CLOUDTRAIL", vpc_id, flush=True)
        time.sleep(20)
    raise RuntimeError("The isolated VPC CreateVpc event did not arrive in CloudTrail S3")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sources = parser.add_mutually_exclusive_group()
    sources.add_argument("--aws-batch-sha", help="SHA-256 of an existing CloudTrail export batch in S3")
    sources.add_argument("--aws-source-vpc", help="Find the new replay VPC creation event in CloudTrail S3")
    args = parser.parse_args()
    if args.aws_batch_sha and not re.fullmatch(r"[0-9a-f]{64}", args.aws_batch_sha):
        parser.error("The batch SHA-256 must contain exactly 64 lowercase hexadecimal digits")

    outputs = json.load(sys.stdin)
    group = outputs["resource_group"]
    match = re.fullmatch(r"rg-ninjasec-audit-replay-([a-z0-9]{8,12})", group)
    if not match:
        raise ValueError("Expected isolated Azure audit resource group")
    suffix = match[1]
    storage = outputs["storage_account"]
    automation = outputs["automation_account_id"]
    workspace = outputs["workspace_id"]
    root = workspace.split("/providers/")[0]
    sub = root.split("/")[2]
    isolated = f"{root}/providers/Microsoft.Automation/automationAccounts/aa-ninjasec-audit-replay-{suffix}"
    shared = f"/subscriptions/{sub}/resourceGroups/rg-ninjasec-compliance/providers/Microsoft.Automation/automationAccounts/ninjasec-oci-audit"
    using_shared = automation.lower() == shared.lower()
    if (not root.lower().endswith("/resourcegroups/" + group)
            or storage != f"nsaudit{suffix}"
            or (not using_shared and automation.lower() != isolated.lower())
            or not workspace.lower().startswith(root.lower() + "/providers/microsoft.operationalinsights/workspaces/")):
        raise ValueError("Output resources are outside the expected test group")

    azure_python = Path(r"C:\Program Files\Microsoft SDKs\Azure\CLI2\python.exe")
    cli = [str(azure_python), "-IBm", "azure.cli"] if azure_python.is_file() else [shutil.which("az") or "az"]
    context = ssl.create_default_context(cafile=os.getenv("REQUESTS_CA_BUNDLE"))

    def token(audience):
        return json.loads(subprocess.check_output(
            [*cli, "account", "get-access-token", "--subscription", sub,
             "--resource", audience, "-o", "json"], text=True,
        ))["accessToken"]

    def request(method, url, access, data=None, headers=None):
        req = urllib.request.Request(url, method=method, data=data, headers={
            "Authorization": f"Bearer {access}", "Content-Type": "application/json", **(headers or {}),
        })
        with urllib.request.urlopen(req, context=context, timeout=50) as result:
            return result.read()

    arm_token = token("https://management.azure.com/")
    claim = arm_token.split(".")[1]
    operator = str(uuid.UUID(json.loads(base64.urlsafe_b64decode(claim + "=" * (-len(claim) % 4)))["oid"]))

    def arm(method, path, api, body=None):
        data = json.dumps(body).encode() if body is not None else None
        payload = request(method, f"https://management.azure.com{path}?api-version={api}", arm_token, data)
        return json.loads(payload) if payload else None

    container = f"{root}/providers/Microsoft.Storage/storageAccounts/{storage}/blobServices/default/containers/audit-logs-aws"
    assignment = f"{container}/providers/Microsoft.Authorization/roleAssignments/{uuid.uuid4()}"
    role = f"/subscriptions/{sub}/providers/Microsoft.Authorization/roleDefinitions/ba92f5b4-2d11-453d-a403-e96b0029c9fe"
    runbook_name = f"Import-AwsAudit-Replay-{suffix}" if using_shared else "Import-AwsAudit"
    checkpoint = f"{automation}/runbooks/{runbook_name}"
    rule_version = "2023-11-01"
    for attempt in range(18):
        status = arm("GET", checkpoint, rule_version)["properties"].get("state")
        if status == "Published":
            break
        time.sleep(10)
    else:
        raise RuntimeError("Azure runbook did not reach Published")

    if args.aws_source_vpc:
        if not re.fullmatch(r"vpc-[0-9a-f]{8,17}", args.aws_source_vpc):
            parser.error("Invalid VPC identifier")
        raw = find_replay_cloudtrail_batch(args.aws_source_vpc, suffix)
        sample = json.loads(raw)
    elif args.aws_batch_sha:
        import boto3

        session = boto3.Session(region_name="us-east-1")
        account = session.client("sts").get_caller_identity()["Account"]
        if account != "533267256700":
            raise ValueError("Unexpected account for the AWS audit batch")
        key = f"export-batches/{args.aws_batch_sha}.json"
        response = session.client("s3").get_object(Bucket=f"ninjasec-audit-{account}", Key=key)
        stream = response["Body"]
        try:
            raw = stream.read(8 * 1024 * 1024 + 1)
        finally:
            stream.close()
        if len(raw) > 8 * 1024 * 1024 or hashlib.sha256(raw).hexdigest() != args.aws_batch_sha:
            raise ValueError("Unexpected size or SHA-256 for the S3 audit batch")
        sample = json.loads(raw)
        print("AZURE_REPLAY_S3_BATCH", key, response["ResponseMetadata"]["RequestId"], flush=True)
    else:
        event = str(uuid.uuid4())
        sample = {
            "schemaVersion": 1, "sources": [{"sha256": hashlib.sha256(event.encode()).hexdigest()}],
            "Records": [{"eventID": event, "eventTime": datetime.now(timezone.utc).isoformat(),
                         "eventName": "NinjaSecSyntheticReplay", "awsRegion": "us-east-1"}],
        }
        raw = json.dumps(sample, sort_keys=True, separators=(",", ":")).encode()
    events = {str(uuid.UUID(record["eventID"])) for record in sample["Records"]}
    if sample.get("schemaVersion") != 1 or not sample.get("sources") or not events or len(events) != len(sample["Records"]):
        raise ValueError("Expected a nonempty audit batch with unique event IDs")
    blob = "aws-audit-" + hashlib.sha256(raw).hexdigest() + ".json"
    blob_url = f"https://{storage}.blob.core.windows.net/audit-logs-aws/{blob}"
    arm("PUT", assignment, "2022-04-01", {"properties": {"principalId": operator, "roleDefinitionId": role}})
    try:
        access = token("https://storage.azure.com/")
        for attempt in range(36):
            try:
                request("PUT", blob_url, access, raw,
                        {"x-ms-blob-type": "BlockBlob", "x-ms-version": "2023-11-03", "If-None-Match": "*"})
                break
            except urllib.error.HTTPError as error:
                if error.code != 403 or attempt == 35:
                    raise
                time.sleep(10)
    finally:
        arm("DELETE", assignment, "2022-04-01")

    job_id = str(uuid.uuid4())
    job_path = f"{automation}/jobs/{job_id}"
    arm("PUT", job_path, rule_version, {"properties": {
        "runbook": {"name": runbook_name}, "parameters": {"BlobName": blob},
    }})
    print("AZURE_REPLAY_JOB", job_id, "RECORDS", len(events), "BLOB", blob, flush=True)
    for _ in range(54):
        status = arm("GET", job_path, rule_version)["properties"]["status"]
        if status == "Completed":
            break
        if status in {"Failed", "Suspended", "Stopped", "Blocked"}:
            raise RuntimeError(f"Azure job {job_id} ended in {status}")
        time.sleep(10)
    else:
        raise RuntimeError(f"Azure job {job_id} timed out")
    workspace_id = arm("GET", workspace, "2022-10-01")["properties"]["customerId"]
    analytics = token("https://api.loganalytics.io")
    query = {"query": f"union (NINJASECAWSAudit_CL | extend Stage='Raw'), "
                      f"(NINJASECAWSAudit() | extend Stage='Deduplicated') "
                      f"| where SourceBlob == '{blob}' | project Stage, EventId"}
    expected = {(stage, event) for stage in ("Raw", "Deduplicated") for event in events}
    for attempt in range(60):
        response = json.loads(request("POST", f"https://api.loganalytics.io/v1/workspaces/{workspace_id}/query",
                                      analytics, json.dumps(query).encode()))
        rows = response["tables"][0]["rows"]
        if {tuple(row) for row in rows} == expected and sum(row[0] == "Deduplicated" for row in rows) == len(events):
            print("AZURE_REPLAY_KQL_MATCH", len(events), blob, flush=True)
            return
        if attempt % 8 == 0:
            print("AZURE_REPLAY_WAITING_FOR_KQL", len(events), blob, flush=True)
        time.sleep(15)
    raise RuntimeError(f"Azure job {job_id} completed but the audit event set was not verified in KQL")


if __name__ == "__main__":
    main()
