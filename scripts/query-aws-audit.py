"""Compare every eventID in a real CloudTrail source with Azure KQL results."""
import json
import argparse
import hashlib
import re
import os
import ssl
import time
import urllib.request
from importlib.machinery import SourceFileLoader
import boto3
az=SourceFileLoader('deploy','scripts/deploy-aws-audit.py').load_module().az
reader=SourceFileLoader('reader','scripts/read-cloudtrail.py').load_module()
key='AWSLogs/533267256700/CloudTrail/us-east-1/2026/11/18/533267256700_CloudTrail_us-east-1_20261118T0840Z_rY6a0QrKVahl0z8K.json.gz'
s3=boto3.Session(profile_name='ninjasec-academy-194766',region_name='us-east-1').client('s3')
args=argparse.ArgumentParser()
args.add_argument('--batch-sha')
options=args.parse_args()
sha=options.batch_sha or 'cfaf995c61f145b51502c6d9f9b34644e727ca49dfff59d55f7054e9e29eb118'
if not re.fullmatch('[a-f0-9]{64}',sha):raise ValueError('Invalid batch SHA-256')
if options.batch_sha:
    data=s3.get_object(Bucket='ninjasec-audit-533267256700',Key='export-batches/'+sha+'.json')['Body'].read()
    if hashlib.sha256(data).hexdigest()!=sha:raise RuntimeError('S3 staged batch hash mismatch')
    batch=json.loads(data)
else:batch=reader.read_batch(s3,'ninjasec-audit-533267256700',[key])
expected={e['eventID'] for e in batch['Records']}
token=az('account','get-access-token','--resource','https://api.loganalytics.io')['accessToken']
context=ssl.create_default_context(cafile=os.environ['REQUESTS_CA_BUNDLE'])
def query(kql):
    req=urllib.request.Request('https://api.loganalytics.io/v1/workspaces/6f4e5048-fa5d-4917-9ad3-a86edf6bf44a/query',data=json.dumps({'query':kql}).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    with urllib.request.urlopen(req,context=context,timeout=60) as r:return json.load(r)['tables'][0]['rows']
blob='aws-audit-'+sha+'.json'
for attempt in range(12):
    rows=query("NINJASECAWSAudit_CL | where SourceBlob == '"+blob+"' | project EventId")
    actual={r[0] for r in rows}
    if actual==expected: break
    if attempt==0:print('WAITING_FOR_COMPLETE_KQL_INGESTION',len(actual),'of',len(expected),flush=True)
    time.sleep(15)
else:raise RuntimeError('KQL eventID set differs from real CloudTrail source')
dedup=query('NINJASECAWSAudit() | where EventId in (dynamic('+json.dumps(sorted(expected))+')) | project EventId')
if len(dedup)!=len(expected) or {r[0] for r in dedup}!=expected:raise RuntimeError('Saved deduplication function failed')
print(json.dumps({'proof':'S3_BLOB_KQL_ALL_EVENTIDS_DEDUP_PASS','sourceCount':len(expected),'rawKqlCount':len(rows),'deduplicatedCount':len(dedup),'referenceEventFound':'ba712b38-0276-467d-a257-f45aaa2fc157' in actual}))
