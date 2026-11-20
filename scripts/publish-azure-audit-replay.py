"""Publish the AWS audit receiver in an isolated Azure replay resource group."""

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


def main():
    automation = os.environ["NINJASEC_REPLAY_AUTOMATION"]
    dcr = os.environ["NINJASEC_REPLAY_DCR"]
    storage = os.environ["NINJASEC_REPLAY_STORAGE"]
    group, _, _ = storage.partition("/providers/")
    match = re.fullmatch(
        r"/subscriptions/([0-9a-f-]{36})/resourceGroups/rg-ninjasec-audit-replay-([a-z0-9]{8,12})",
        group,
        re.I,
    )
    if not match:
        raise ValueError("Only isolated audit replay resource groups are allowed")
    subscription, suffix = match.groups()
    automation_name = f"aa-ninjasec-audit-replay-{suffix}"
    isolated = f"{group}/providers/Microsoft.Automation/automationAccounts/{automation_name}"
    shared = f"/subscriptions/{subscription}/resourceGroups/rg-ninjasec-compliance/providers/Microsoft.Automation/automationAccounts/ninjasec-oci-audit"
    external = automation.lower() == shared.lower()
    storage_name = f"nsaudit{suffix}"
    if (not external and automation.lower() != isolated.lower()
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
    variable_name = f"AwsAuditReplayDestination-{suffix}" if external else "AwsAuditDestination"
    runbook_name = f"Import-AwsAudit-Replay-{suffix}" if external else "Import-AwsAudit"
    runbook = f"{automation}/runbooks/{runbook_name}"
    variable = f"{automation}/variables/{variable_name}"
    if sys.argv[1:] == ["--remove"]:
        if external:
            for resource in (runbook, variable):
                try:
                    arm("DELETE", resource, api)
                except urllib.error.HTTPError as error:
                    if error.code != 404:
                        raise
                for attempt in range(18):
                    try:
                        arm("GET", resource, api)
                    except urllib.error.HTTPError as error:
                        if error.code == 404:
                            break
                        raise
                    time.sleep(5)
                else:
                    raise RuntimeError("Azure replay runbook or variable is still present")
            print("AZURE_SHARED_REPLAY_REMOVED", runbook_name)
        return
    if external:
        arm("PUT", runbook, api, {
            "location": "westus",
            "properties": {
                "runbookType": "PowerShell72", "logProgress": False, "logVerbose": False,
                "description": f"NINJA-SEC isolated replay {suffix}",
            },
        })
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
    arm("PUT", variable, api,
        {"name": variable_name, "properties": {"isEncrypted": False, "value": json.dumps(config)}})
    source = Path(__file__).with_name("import-aws-audit.ps1").read_bytes()
    if external:
        source = source.replace(b"-Name 'AwsAuditDestination'", f"-Name '{variable_name}'".encode(), 1)
    arm("PUT", f"{runbook}/draft/content", api, source)
    arm("POST", f"{runbook}/publish", api, {})
    print("AZURE_REPLAY_AUDIT_PUBLISH_REQUEST_ACCEPTED", runbook_name)


if __name__ == "__main__":
    main()
