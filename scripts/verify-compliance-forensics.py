"""Validate deployed workbook queries against real audit records and query-only freshness fixtures."""
import importlib.util
import json
from pathlib import Path
import time
import urllib.request
import urllib.error

spec=importlib.util.spec_from_file_location('forensics','scripts/deploy-compliance-forensics.py')
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
def query(kql):
    result=f.az('rest','--method','post','--url','https://api.loganalytics.io/v1/workspaces/6f4e5048-fa5d-4917-9ad3-a86edf6bf44a/query','--resource','https://api.loganalytics.io','--body',json.dumps({'query':kql}))
    if result.get('error'):raise RuntimeError('KQL returned partial/error result')
    table=result['tables'][0]
    return [dict(zip((c['name'] for c in table['columns']),row)) for row in table['rows']]

ids={'4d61eb73-4ca7-458a-8f20-85681252acd3','83abefec-0cb6-4b55-acc2-b7a19fd74071'}
for attempt in range(12):
    aws=query('NINJASECMulticloudAudit() | where '+f.NETWORK_FILTER+' | where EventId in (dynamic('+json.dumps(sorted(ids))+'))')
    oci=query('NINJASECMulticloudAudit() | where Provider == "OCI" and TimestampOrigin == "SOURCE_EVENT_TIME" and TimeGenerated between (datetime(2026-11-11) .. datetime(2026-11-12)) and isnotempty(Identity) and isnotempty(ResourceId) | where '+f.NETWORK_FILTER+' | take 3')
    if {r['EventId'] for r in aws}==ids and all(r['TimestampOrigin']=='SOURCE_EVENT_TIME' for r in aws) and oci:break
    if attempt==0:print('WAITING_FOR_ENRICHED_REAL_EVENTS',len(aws),len(oci),flush=True)
    time.sleep(15)
else:raise RuntimeError('Real AWS and OCI forensic evidence incomplete')
assert all(r['Provider']=='AWS' and 'sg-011c9977a0a1084c5' in r['ResourceId'] and r['Identity'].startswith('arn:aws:sts::533267256700:') for r in aws)
assert all(r['Identity'].startswith('ocid1.') and r['ResourceId'].startswith('ocid1.') for r in oci)
assert all(r['TimeGenerated'].startswith('2026-11-11') for r in oci)
print('REAL_AWS_SG_IDENTITY_RESOURCE_TIME_PASS',json.dumps(aws,ensure_ascii=False),flush=True)
print('REAL_OCI_IDENTITY_RESOURCE_TIME_PASS',json.dumps(oci,ensure_ascii=False),flush=True)
historical=query('NINJASECOCIAudit_CL | where EventId == "'+oci[0]['EventId']+'" and isnotempty(OriginalEventTime) | extend IngestedAt=ingestion_time() | summarize arg_max(IngestedAt, *) by EventId | project EventId, SourceEventTime=todatetime(OriginalEventTime), AzureTimeGenerated=TimeGenerated')
assert historical and historical[0]['SourceEventTime'].startswith('2026-11-11')
assert historical[0]['AzureTimeGenerated']!=historical[0]['SourceEventTime']
print('HISTORICAL_SOURCE_TIME_PRESERVED_DESPITE_AZURE_TIMEGENERATED_REPLACEMENT',json.dumps(historical),flush=True)

blobs={
    'oci-audit-2026-11-11-1ff55bd0949a227728ed3cafb94e179aa0c1855854f768d02f372119dde0e272.json':1970,
    'oci-audit-2026-11-17-eb7c5d212e516764bdf5c08ebe98da53d05ff7decdf2d3de46c123841b66447a.json':1219,
}
coverage_kql='NINJASECOCIAudit_CL | where SourceBlob in (dynamic('+json.dumps(list(blobs))+')) | extend IngestedAt=ingestion_time() | summarize arg_max(IngestedAt,*) by EventId | summarize Rows=count(),WithOriginalTime=countif(isnotempty(OriginalEventTime)) by SourceBlob'
for attempt in range(16):
    coverage=query(coverage_kql)
    if len(coverage)==2 and all(r['Rows']==blobs[r['SourceBlob']] and r['WithOriginalTime']==r['Rows'] for r in coverage):break
    if attempt==0:print('WAITING_FOR_COMPLETE_SOURCE_TIME_COVERAGE',json.dumps(coverage),flush=True)
    time.sleep(15)
else:raise RuntimeError('Original date coverage is incomplete in the full OCI batches')
print('COMPLETE_OCI_SOURCE_TIME_COVERAGE_3189_OF_3189_PASS',json.dumps(coverage),flush=True)

template=json.loads(Path('azure/compliance-forensics.json').read_text(encoding='utf-8'))
expected=json.loads(next(r for r in template['resources'] if r['type']=='Microsoft.Insights/workbooks')['properties']['serializedData'])
saved=f.arm('GET',f.WORKBOOK+'?canFetchContent=true','2023-06-01')
actual=json.loads(saved['properties']['serializedData'])
assert actual==expected, 'Saved workbook differs from IaC'
count=0
for item in actual['items']:
    if item.get('type')==3:
        rows=query(item['content']['query'])
        print('WORKBOOK_QUERY_PASS',item['content'].get('title',item['name']),'rows='+str(len(rows)),flush=True)
        count+=1

tail=f.FRESHNESS[f.FRESHNESS.index('datatable(Provider:string)'):]
empty='let observed=datatable(Provider:string, Events:long, LastEvent:datetime, LastIngestion:datetime)[];\n'
assert {r['Status'] for r in query(empty+tail)}=={'SIN DATOS'}
for last_event,last_ingestion,status in [('ago(48h)','ago(48h)','INGESTA ATRASADA'),('ago(7d)','now()','EVENTOS ANTIGUOS / REVISAR ORIGEN')]:
    fixture='let observed=print Provider="AWS",Events=long(1),LastEvent='+last_event+',LastIngestion='+last_ingestion+';\n'
    assert next(r for r in query(fixture+tail) if r['Provider']=='AWS')['Status']==status
print('QUERY_ONLY_EMPTY_STALE_AND_HISTORICAL_STATUS_PASS; NO_FIXTURE_INGESTED',flush=True)
print('CURRENT_SOURCE_STATUS',json.dumps(query(f.FRESHNESS),ensure_ascii=False),flush=True)
print('WORKBOOK_REMOTE_EXACT_MATCH_AND_ALL_'+str(count)+'_QUERIES_PASS',flush=True)
