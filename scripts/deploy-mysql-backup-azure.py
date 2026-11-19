"""Schedule a managed-identity OCI->Azure backup copy; no new passwords/webhooks."""
import datetime as dt
from importlib.machinery import SourceFileLoader
import json
import os
from pathlib import Path
import ssl
import urllib.request
import urllib.error
import uuid

az=SourceFileLoader('azure_cli_helper','scripts/deploy-aws-audit.py').load_module().az
ROOT='/subscriptions/020556eb-782f-4afc-84d3-39cd392763ba/resourceGroups/rg-ninjasec-compliance'
ACCOUNT=ROOT+'/providers/Microsoft.Automation/automationAccounts/ninjasec-oci-audit'

def main():
    token=az('account','get-access-token','--resource','https://management.azure.com/')['accessToken']
    context=ssl.create_default_context(cafile=os.environ['REQUESTS_CA_BUNDLE'])
    def arm(method,path,data=None,raw=False):
        body=data.encode() if raw else json.dumps(data).encode() if data is not None else None
        request=urllib.request.Request('https://management.azure.com'+path+'?api-version=2023-11-01',data=body,method=method,headers={'Authorization':'Bearer '+token,'Content-Type':'text/plain' if raw else 'application/json'})
        try:
            with urllib.request.urlopen(request,context=context,timeout=60) as r:
                result=r.read().decode();return json.loads(result) if result else None
        except urllib.error.HTTPError as e:raise RuntimeError('ARM '+str(e.code)+' '+e.read().decode()[:1000]) from None
    account=az('resource','show','--ids',ACCOUNT)
    scope=ROOT+'/providers/Microsoft.Storage/storageAccounts/ninjaseccompliance63ba/blobServices/default/containers/db-backups'
    for role in ['Storage Blob Data Reader','NINJA-SEC Audit Blob Writer']:
        az('role','assignment','create','--assignee-object-id',account['identity']['principalId'],'--assignee-principal-type','ServicePrincipal','--role',role,'--scope',scope)
    config={'namespace':'idyjnbepyaq2','bucket':'ninjasec-backup-staging','container':'https://ninjaseccompliance63ba.blob.core.windows.net/db-backups'}
    arm('PUT',ACCOUNT+'/variables/MysqlBackupDestination',{'name':'MysqlBackupDestination','properties':{'isEncrypted':False,'value':json.dumps(config)}})
    name='Copy-MysqlBackupToAzure'
    arm('PUT',ACCOUNT+'/runbooks/'+name,{'name':name,'location':account['location'],'properties':{'runbookType':'PowerShell72','logProgress':False,'logVerbose':False,'description':'Copy fresh OCI MySQL dump to existing immutable Azure container; verify SHA256 both sides'}})
    arm('PUT',ACCOUNT+'/runbooks/'+name+'/draft/content',Path('scripts/copy-mysql-backup-to-azure.ps1').read_text(),raw=True)
    arm('POST',ACCOUNT+'/runbooks/'+name+'/publish',{})
    start=dt.datetime.now(dt.timezone.utc).replace(hour=7,minute=15,second=0,microsecond=0)
    if start<dt.datetime.now(dt.timezone.utc)+dt.timedelta(minutes=5):start+=dt.timedelta(days=1)
    schedule='ninjasec-mysql-backup-daily'
    arm('PUT',ACCOUNT+'/schedules/'+schedule,{'name':schedule,'properties':{'description':'Daily OCI archive copy at 07:15 UTC; VM backup cron runs 07:00 UTC','startTime':start.isoformat(),'frequency':'Day','interval':1,'timeZone':'UTC'}})
    link=str(uuid.uuid5(uuid.NAMESPACE_URL,ACCOUNT+'/'+schedule))
    arm('PUT',ACCOUNT+'/jobSchedules/'+link,{'properties':{'schedule':{'name':schedule},'runbook':{'name':name},'parameters':{}}})
    job=str(uuid.uuid4());arm('PUT',ACCOUNT+'/jobs/'+job,{'properties':{'runbook':{'name':name},'parameters':{}}})
    print('MYSQL_AZURE_RUNBOOK',name,'JOB',job,'DAILY_UTC',start.isoformat(),flush=True)

if __name__=='__main__':main()
