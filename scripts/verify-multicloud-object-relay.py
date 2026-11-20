"""Move one synthetic event through disposable AWS, OCI, and Azure stores."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import ssl
import time
import urllib.error
import urllib.request
import uuid
from importlib.machinery import SourceFileLoader

import boto3
import oci

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "terraform/environments/integration-proof/terraform.tfstate"


def main():
    stores = json.loads(STATE.read_text(encoding="utf-8"))["outputs"]["proof_stores"]["value"]
    aws_bucket = stores["aws_bucket"]
    oci_bucket = stores["oci_bucket"]
    namespace = stores["oci_namespace"]
    account = stores["azure_storage_account"]
    container = stores["azure_container"]
    if (
        not aws_bucket.startswith("ninjasec-m105-")
        or oci_bucket != aws_bucket
        or account != "nsm105" + aws_bucket.removeprefix("ninjasec-m105-")
        or container != "integration-proof"
    ):
        raise RuntimeError("Unexpected destination. Use only the isolated Terraform state.")

    aws = boto3.Session(region_name="us-east-1")
    if aws.client("sts").get_caller_identity()["Account"] != "533267256700":
        raise RuntimeError("Unexpected AWS account.")
    s3 = aws.client("s3")
    storage = oci.object_storage.ObjectStorageClient(
        oci.config.from_file(profile_name="NINJA_SEC_TERRAFORM")
    )
    az = SourceFileLoader("ninjasec_az", str(ROOT / "scripts/deploy-aws-audit.py")).load_module().az
    token = az("account", "get-access-token", "--resource", "https://storage.azure.com/")["accessToken"]
    context = ssl.create_default_context(cafile=os.environ["REQUESTS_CA_BUNDLE"])
    event_id = str(uuid.uuid4())
    key = f"{event_id}.json"
    payload = json.dumps({
        "id": event_id, "type": "ninjasec.integration.proof",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }, sort_keys=True).encode()
    azure_url = f"https://{account}.blob.core.windows.net/{container}/{key}"
    headers = {"Authorization": f"Bearer {token}", "x-ms-version": "2023-11-03"}

    def blob(method, data=None):
        request = urllib.request.Request(
            azure_url, data=data, method=method,
            headers={**headers, "x-ms-blob-type": "BlockBlob"} if data is not None else headers,
        )
        return urllib.request.urlopen(request, context=context, timeout=20)

    cleanup = []
    try:
        aws_write = s3.put_object(Bucket=aws_bucket, Key=key, Body=payload)
        cleanup.append(("AWS", lambda: s3.delete_object(Bucket=aws_bucket, Key=key)))
        with s3.get_object(Bucket=aws_bucket, Key=key)["Body"] as body:
            from_aws = body.read()
        oci_write = storage.put_object(namespace, oci_bucket, key, from_aws)
        cleanup.append(("OCI", lambda: storage.delete_object(namespace, oci_bucket, key)))
        with storage.get_object(namespace, oci_bucket, key).data as body:
            from_oci = body.content
        for attempt in range(18):
            try:
                with blob("PUT", from_oci) as response:
                    azure_write = response.headers.get("x-ms-request-id")
                break
            except urllib.error.HTTPError as error:
                if error.code != 403 or attempt == 17:
                    raise
                time.sleep(10)  # Allow the new container-scoped role to propagate.
        cleanup.append(("Azure", lambda: blob("DELETE").close()))
        with blob("GET") as response:
            from_azure = response.read()
        if not payload == from_aws == from_oci == from_azure:
            raise RuntimeError("The object changed during transit.")
        print(json.dumps({
            "event_id": event_id, "sha256": hashlib.sha256(payload).hexdigest(),
            "aws_request_id": aws_write["ResponseMetadata"]["RequestId"],
            "oci_request_id": oci_write.headers.get("opc-request-id"),
            "azure_request_id": azure_write,
        }), flush=True)
    finally:
        failures = []
        for platform, remove in reversed(cleanup):
            try:
                remove()
                print(f"{platform}: synthetic object removed", flush=True)
            except Exception as error:
                failures.append(f"{platform}: {type(error).__name__}")
        if failures:
            raise RuntimeError("Synthetic object cleanup failed: " + ", ".join(failures))


if __name__ == "__main__":
    main()
