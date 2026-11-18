"""Publish Azure managed-identity receiver; persist webhook only in approved secret stores."""
import datetime as dt
import json
from pathlib import Path
import ssl
import os
import subprocess
import urllib.request
import urllib.error
import boto3
from importlib.machinery import SourceFileLoader
az=SourceFileLoader('deploy','scripts/deploy-aws-audit.py').load_module().az

root='/subscriptions/020556eb-782f-4afc-84d3-39cd392763ba/resourceGroups/rg-ninjasec-compliance'
account=root+'/providers/Microsoft.Automation/automationAccounts/ninjasec-oci-audit'
token=az('account','get-access-token','--resource','https://management.azure.com/')['accessToken']
context=ssl.create_default_context(cafile=os.environ['REQUESTS_CA_BUNDLE'])
def arm(method,path,body=None,raw=False):
    data=body.encode() if raw else json.dumps(body).encode() if body is not None else None
    req=urllib.request.Request('https://management.azure.com'+path+('?api-version=2023-11-01' if '?' not in path else ''),data=data,method=method,headers={'Authorization':'Bearer '+token,'Content-Type':'text/plain' if raw else 'application/json'})
    try:
        with urllib.request.urlopen(req,context=context,timeout=120) as response:
            text=response.read().decode();return json.loads(text) if text else None
    except urllib.error.HTTPError as exc:
        raise RuntimeError('ARM HTTP '+str(exc.code)+' '+exc.read().decode()[:1200]) from None

arm('PATCH',account,{'properties':{'disableLocalAuth':False}})
dcr=az('resource','show','-g','rg-ninjasec-compliance','-n','ninjasec-aws-audit','--resource-type','Microsoft.Insights/dataCollectionRules')
config={'container':'https://ninjaseccompliance63ba.blob.core.windows.net/audit-logs-aws','checkpoints':'https://ninjaseccompliance63ba.blob.core.windows.net/pipeline-state','ingestion':dcr['properties']['endpoints']['logsIngestion']+'/dataCollectionRules/'+dcr['properties']['immutableId']+'/streams/Custom-NINJASECAWSAudit_CL?api-version=2023-01-01'}
arm('PUT',account+'/variables/AwsAuditDestination',{'name':'AwsAuditDestination','properties':{'isEncrypted':False,'value':json.dumps(config)}})
identity=az('resource','show','--ids',account)['identity']['principalId']
for role,scope in [
    ('Storage Blob Data Reader',root+'/providers/Microsoft.Storage/storageAccounts/ninjaseccompliance63ba/blobServices/default/containers/audit-logs-aws'),
    ('NINJA-SEC Audit Blob Writer',root+'/providers/Microsoft.Storage/storageAccounts/ninjaseccompliance63ba/blobServices/default/containers/audit-logs-aws'),
    ('Storage Blob Data Contributor',root+'/providers/Microsoft.Storage/storageAccounts/ninjaseccompliance63ba/blobServices/default/containers/pipeline-state'),
    ('Monitoring Metrics Publisher',dcr['id'])]:
    az('role','assignment','create','--assignee-object-id',identity,'--assignee-principal-type','ServicePrincipal','--role',role,'--scope',scope)
arm('PUT',account+'/runbooks/Import-AwsAudit/draft/content',Path('scripts/import-aws-audit.ps1').read_text(),True)
arm('POST',account+'/runbooks/Import-AwsAudit/publish',{})
secretPath=Path('E:/NINJA-SEC/Credenciales de Acceso/azure-audit-webhook.json')
if secretPath.exists(): value=json.loads(secretPath.read_text())
else:
    uri=arm('POST',account+'/webhooks/generateUri?api-version=2024-10-23',{})
    expiry=(dt.datetime.now(dt.timezone.utc)+dt.timedelta(days=30)).isoformat()
    arm('PUT',account+'/webhooks/AwsAuditReceiver?api-version=2024-10-23',{'name':'AwsAuditReceiver','properties':{'uri':uri,'isEnabled':True,'expiryTime':expiry,'runbook':{'name':'Import-AwsAudit'}}})
    value={'webhookUrl':uri,'expiresAt':expiry}
    secretPath.write_text(json.dumps(value),encoding='utf-8')
if os.name == 'nt':
    principal=os.environ['USERDOMAIN']+'\\'+os.environ['USERNAME']
    result=subprocess.run(['icacls',str(secretPath),'/inheritance:r','/grant:r',principal+':(F)','*S-1-5-18:(F)','*S-1-5-32-544:(F)'],capture_output=True,text=True)
    if result.returncode: raise RuntimeError('Could not restrict webhook credential file')
session=boto3.Session(profile_name='ninjasec-academy-194766',region_name='us-east-1')
session.client('secretsmanager').put_secret_value(SecretId='ninjasec/azure-audit-writer',SecretString=json.dumps(value))
print('AZURE_RECEIVER_PUBLISHED_WEBHOOK_SAVED_NO_SHARED_KEYS')
