"""Publish the AWS audit receiver in an isolated Azure replay resource group."""

import json
import os
from pathlib import Path
import re
import shutil
import ssl
import subprocess
import urllib.request


def main():
    automation = os.environ["NINJASEC_REPLAY_AUTOMATION"]
    dcr = os.environ["NINJASEC_REPLAY_DCR"]
    storage = os.environ["NINJASEC_REPLAY_STORAGE"]
    group, _, resource = automation.partition("/providers/")
    match = re.fullmatch(
        r"/subscriptions/([0-9a-f-]{36})/resourceGroups/rg-ninjasec-audit-replay-([a-z0-9]{8,12})",
        group,
        re.I,
    )
    if not match:
        raise ValueError("Only isolated audit replay resource groups are allowed")
    subscription, suffix = match.groups()
    automation_name = f"aa-ninjasec-audit-replay-{suffix}"
    storage_name = f"nsaudit{suffix}"
    if (resource.lower() != f"microsoft.automation/automationaccounts/{automation_name}".lower()
            or dcr.lower() != (group + f"/providers/Microsoft.Insights/dataCollectionRules/aws-audit-{suffix}").lower()
            or storage.lower() != (group + f"/providers/Microsoft.Storage/storageAccounts/{storage_name}").lower()):
        raise ValueError("Replay resource names or resource group do not match")

    # Invoke the same cached Azure CLI session used by the Terraform provider.
    windows_cli_python = Path(r"C:\Program Files\Microsoft SDKs\Azure\CLI2\python.exe")
    cli = [str(windows_cli_python), "-IBm", "azure.cli"] if windows_cli_python.is_file() else [shutil.which("az") or "az"]
    token = json.loads(subprocess.check_output(
        [*cli, "account", "get-access-token", "--subscription", subscription,
         "--resource", "https://management.azure.com/", "-o", "json"],
        text=True,
    ))["accessToken"]
    context = ssl.create_default_context(cafile=os.getenv("REQUESTS_CA_BUNDLE"))

    def arm(method, path, version, body=None):
        content_type = "text/plain" if isinstance(body, bytes) else "application/json"
        data = body if isinstance(body, bytes) else json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            f"https://management.azure.com{path}?api-version={version}", method=method, data=data,
            headers={"Authorization": f"Bearer {token}", "Content-Type": content_type},
        )
        with urllib.request.urlopen(request, context=context, timeout=90) as response:
            content = response.read()
            return json.loads(content) if content else None

    api = "2023-11-01"
    rule = arm("GET", dcr, "2023-03-11")["properties"]
    ingestion = rule["endpoints"]["logsIngestion"].rstrip("/")
    if not re.fullmatch(r"https://[a-z0-9.-]+\.monitor\.azure\.com", ingestion):
        raise ValueError("Unexpected data collection endpoint")
    base = f"https://{storage_name}.blob.core.windows.net"
    config = {
        "container": f"{base}/audit-logs-aws",
        "checkpoints": f"{base}/pipeline-state",
        "ingestion": f"{ingestion}/dataCollectionRules/{rule['immutableId']}/streams/Custom-NINJASECAWSAudit_CL?api-version=2023-01-01",
    }
    arm("PUT", f"{automation}/variables/AwsAuditDestination", api,
        {"name": "AwsAuditDestination", "properties": {"isEncrypted": False, "value": json.dumps(config)}})
    runbook = f"{automation}/runbooks/Import-AwsAudit"
    source = Path(__file__).with_name("import-aws-audit.ps1").read_bytes()
    arm("PUT", f"{runbook}/draft/content", api, source)
    arm("POST", f"{runbook}/publish", api, {})
    print("AZURE_REPLAY_AUDIT_PUBLISH_REQUEST_ACCEPTED", automation_name)


if __name__ == "__main__":
    main()
