"""Verify real archive integrity and WORM; temporary human data role is removed in finally."""
import hashlib
import json
import os
import ssl
import time
import urllib.request
import urllib.error
from importlib.machinery import SourceFileLoader
az=SourceFileLoader('deploy','scripts/deploy-aws-audit.py').load_module().az

blob='aws-audit-cfaf995c61f145b51502c6d9f9b34644e727ca49dfff59d55f7054e9e29eb118.json'
scope='/subscriptions/020556eb-782f-4afc-84d3-39cd392763ba/resourceGroups/rg-ninjasec-compliance/providers/Microsoft.Storage/storageAccounts/ninjaseccompliance63ba/blobServices/default/containers/audit-logs-aws'
principal='9749d108-d22b-40f0-b6ae-c327cc58b95d'
existing=az('role','assignment','list','--scope',scope,'--query',"[?principalId=='"+principal+"' && roleDefinitionName=='Storage Blob Data Contributor']")
assignment=None
try:
    if not existing:
        assignment=az('role','assignment','create','--assignee-object-id',principal,'--assignee-principal-type','User','--role','Storage Blob Data Contributor','--scope',scope)['id']
    token=az('account','get-access-token','--resource','https://storage.azure.com/')['accessToken']
    context=ssl.create_default_context(cafile=os.environ['REQUESTS_CA_BUNDLE'])
    url='https://ninjaseccompliance63ba.blob.core.windows.net/audit-logs-aws/'+blob
    headers={'Authorization':'Bearer '+token,'x-ms-version':'2023-11-03'}
    for attempt in range(12):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=headers),context=context) as response: body=response.read()
            break
        except urllib.error.HTTPError as exc:
            if exc.code==403 and attempt<11: time.sleep(10);continue
            raise RuntimeError('Archive GET HTTP '+str(exc.code)) from None
    sha=hashlib.sha256(body).hexdigest()
    if blob!='aws-audit-'+sha+'.json': raise RuntimeError('Archive hash mismatch')
    events=json.loads(body)['Records']
    expected='ba712b38-0276-467d-a257-f45aaa2fc157'
    if expected not in {e['eventID'] for e in events}: raise RuntimeError('Expected real event missing')
    try:
        urllib.request.urlopen(urllib.request.Request(url,method='DELETE',headers=headers),context=context)
        raise RuntimeError('WORM DELETE unexpectedly succeeded')
    except urllib.error.HTTPError as exc:
        code=exc.headers.get('x-ms-error-code')
        if exc.code!=409 or code!='BlobImmutableDueToPolicy':raise RuntimeError('Unexpected delete result '+str(exc.code)+' '+str(code)) from None
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),context=context) as response:
        if hashlib.sha256(response.read()).hexdigest()!=sha:raise RuntimeError('Archive changed after DELETE')
    print(json.dumps({'proof':'ARCHIVE_SHA_EVENTID_WORM_DELETE409_PASS','blob':blob,'sha256':sha,'records':len(events),'eventID':expected}))
finally:
    if assignment:
        az('role','assignment','delete','--ids',assignment)
        print('TEMPORARY_DATA_ROLE_REMOVED')
