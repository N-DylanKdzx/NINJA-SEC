"""Enrich OCI audit and deploy verified AWS/OCI forensic queries and workbook."""
import json
import os
from pathlib import Path
import ssl
import urllib.request
from importlib.machinery import SourceFileLoader

az = SourceFileLoader('deploy', 'scripts/deploy-aws-audit.py').load_module().az
ROOT = '/subscriptions/020556eb-782f-4afc-84d3-39cd392763ba/resourceGroups/rg-ninjasec-compliance'
WORKSPACE = ROOT + '/providers/Microsoft.OperationalInsights/workspaces/ninjasec-law'
AUTOMATION = ROOT + '/providers/Microsoft.Automation/automationAccounts/ninjasec-oci-audit'
WORKBOOK = ROOT + '/providers/Microsoft.Insights/workbooks/5ec9a0d2-1a5a-4e81-a7a4-698f9e43b035'
CONTEXT = ssl.create_default_context(cafile=os.environ['REQUESTS_CA_BUNDLE'])

def arm(method, path, version, value=None, raw=False):
    token = az('account', 'get-access-token', '--resource', 'https://management.azure.com/')['accessToken']
    data = value.encode() if raw else json.dumps(value).encode() if value is not None else None
    separator = '&' if '?' in path else '?'
    req = urllib.request.Request('https://management.azure.com'+path+separator+'api-version='+version, data=data, method=method,
        headers={'Authorization':'Bearer '+token,'Content-Type':'text/plain' if raw else 'application/json'})
    with urllib.request.urlopen(req, context=CONTEXT, timeout=120) as response:
        text = response.read().decode('utf-8-sig')
        return json.loads(text) if text else None

UNIFIED = '''union
(NINJASECAWSAudit_CL | project TimeGenerated=coalesce(todatetime(column_ifexists("OriginalEventTime","")),column_ifexists("EventTime",datetime(null)),TimeGenerated), TimestampOrigin=iff(isnotnull(coalesce(todatetime(column_ifexists("OriginalEventTime","")),column_ifexists("EventTime",datetime(null)))),"SOURCE_EVENT_TIME","LEGACY_AZURE_TIME_UNVERIFIED"), Provider="AWS", EventId, EventName, Identity=UserArn, Region, ResourceId, ResponseStatus, SourceIp, SourceBlob, IngestedAt=ingestion_time()),
(NINJASECOCIAudit_CL | project TimeGenerated=coalesce(todatetime(column_ifexists("OriginalEventTime","")),column_ifexists("EventTime",datetime(null)),TimeGenerated), TimestampOrigin=iff(isnotnull(coalesce(todatetime(column_ifexists("OriginalEventTime","")),column_ifexists("EventTime",datetime(null)))),"SOURCE_EVENT_TIME","LEGACY_AZURE_TIME_UNVERIFIED"), Provider="OCI", EventId, EventName, Identity=tostring(column_ifexists("Identity", "")), Region, ResourceId, ResponseStatus, SourceIp=tostring(column_ifexists("SourceIp", "")), SourceBlob=tostring(column_ifexists("SourceBlob", "")), IngestedAt=ingestion_time())
| where isnotempty(EventId)
| summarize arg_max(IngestedAt, *) by Provider, EventId'''

NETWORK_FILTER = '''EventName in~ ("CreateSecurityGroup", "DeleteSecurityGroup", "AuthorizeSecurityGroupIngress", "RevokeSecurityGroupIngress", "AuthorizeSecurityGroupEgress", "RevokeSecurityGroupEgress", "ModifySecurityGroupRules", "CreateRoute", "DeleteRoute", "ReplaceRoute", "CreateNetworkAclEntry", "ReplaceNetworkAclEntry", "DeleteNetworkAclEntry", "CreateNetworkSecurityGroup", "DeleteNetworkSecurityGroup", "UpdateNetworkSecurityGroup", "AddNetworkSecurityGroupSecurityRules", "UpdateNetworkSecurityGroupSecurityRules", "RemoveNetworkSecurityGroupSecurityRules", "UpdateSecurityList", "UpdateRouteTable", "CreateSecurityList", "CreateRouteTable")'''

FORENSIC = 'NINJASECMulticloudAudit()\n| where TimeGenerated > ago(24h)\n| where '+NETWORK_FILTER+'''
| extend Identity=iff(isempty(Identity), "NO CAPTURADA (histórico)", Identity)
| project TimeGenerated, TimestampOrigin, Provider, EventName, Identity, ResourceId, Region, ResponseStatus, SourceIp, EventId, SourceBlob
| order by TimeGenerated desc'''

FRESHNESS = '''let observed=NINJASECMulticloudAudit()
| summarize Events=count(), LastEvent=max(TimeGenerated), LastIngestion=max(IngestedAt) by Provider;
datatable(Provider:string)["AWS","OCI"]
| join kind=leftouter observed on Provider
| extend AgeHours=round(datetime_diff('second', now(), LastIngestion)/3600.0,2), EventAgeHours=round(datetime_diff('second', now(), LastEvent)/3600.0,2)
| extend Status=case(isnull(LastIngestion),"SIN DATOS",AgeHours>26,"INGESTA ATRASADA",EventAgeHours>26,"EVENTOS ANTIGUOS / REVISAR ORIGEN","DENTRO DE VENTANA DIARIA")
| project Provider, Status, LastEventUTC=iff(isnull(LastEvent),"—",strcat(format_datetime(LastEvent,'yyyy-MM-dd HH:mm:ss.fff'),'Z')), LastIngestionUTC=iff(isnull(LastIngestion),"—",strcat(format_datetime(LastIngestion,'yyyy-MM-dd HH:mm:ss.fff'),'Z')), AgeHours, EventAgeHours, Events=coalesce(Events,0)
| order by Provider asc'''

DISPLAY_UTC = " | extend EventTimeUTC=strcat(format_datetime(TimeGenerated,'yyyy-MM-dd HH:mm:ss.fff'),'Z') | project-away TimeGenerated"

def query_item(name, title, query, days=1, visualization='table'):
    return {'type':3,'name':name,'content':{'version':'KqlItem/1.0','title':title,'query':query,'size':0,
        'queryType':0,'resourceType':'microsoft.operationalinsights/workspaces','crossComponentResources':[WORKSPACE],
        'timeContext':{'durationMs':days*86400000},'visualization':visualization}}

def main():
    table=arm('GET',WORKSPACE+'/tables/NINJASECOCIAudit_CL','2022-10-01')
    columns=table['properties']['schema']['columns']
    for name in ['Identity','SourceIp','SourceBlob','EventTime','OriginalEventTime']:
        if not any(c['name']==name for c in columns):columns.append({'name':name,'type':'datetime' if name=='EventTime' else 'string'})
    table_resource={'type':'Microsoft.OperationalInsights/workspaces/tables','apiVersion':'2022-10-01',
        'name':'ninjasec-law/NINJASECOCIAudit_CL','properties':{'schema':{'name':'NINJASECOCIAudit_CL','columns':columns},'retentionInDays':30,'totalRetentionInDays':30,'plan':'Analytics'}}
    dcr=arm('GET',ROOT+'/providers/Microsoft.Insights/dataCollectionRules/ninjasec-oci-audit','2023-03-11')
    props=dcr['properties']
    for key in ['provisioningState','immutableId','endpoints']:props.pop(key,None)
    stream=props['streamDeclarations']['Custom-NINJASECOCIAudit_CL']['columns']
    for name in ['Identity','SourceIp','SourceBlob','EventTime','OriginalEventTime']:
        if not any(c['name']==name for c in stream):stream.append({'name':name,'type':'datetime' if name=='EventTime' else 'string'})
    dcr_resource={'type':'Microsoft.Insights/dataCollectionRules','apiVersion':'2023-03-11','name':'ninjasec-oci-audit',
        'location':dcr['location'],'kind':dcr['kind'],'properties':props,
        'dependsOn':["[resourceId('Microsoft.OperationalInsights/workspaces/tables', 'ninjasec-law', 'NINJASECOCIAudit_CL')]"]}
    workbook=arm('GET',WORKBOOK+'?canFetchContent=true','2023-06-01')
    data=json.loads(workbook['properties']['serializedData'])
    # Preserve existing content; replace the obsolete single-table panel and append named, idempotent panels.
    data['items']=[i for i in data['items'] if not i.get('name','').startswith('ninjasec-multicloud-')]
    for item in data['items']:
        content=item.get('content',{})
        if item.get('name')=='texto - 2':
            content['json']='## NINJA-SEC · Cumplimiento y trazabilidad\nAuditoría real de AWS y OCI centralizada en Azure. Revise primero la antigüedad de cada fuente y después los cambios de seguridad y red. Las tablas muestran UTC con sufijo Z; los gráficos usan la zona horaria del portal.'
        if isinstance(content,dict) and content.get('query','').startswith('union withsource='):
            content.update(query='NINJASECMulticloudAudit() | where TimeGenerated > ago(24h) | summarize Eventos=count() by Provider | render barchart',title='Eventos reales por proveedor · 24 h')
            content['crossComponentResources']=[WORKSPACE]
        if isinstance(content,dict) and ('NINJASECAuditLogs_CL' in content.get('query','') or content.get('title')=='Últimos eventos reales AWS / OCI'):
            content.update(query='NINJASECMulticloudAudit() | where TimeGenerated > ago(24h) | project TimeGenerated, Provider, EventName, Identity, ResourceId, EventId | order by TimeGenerated desc | take 100'+DISPLAY_UTC,title='Últimos eventos reales AWS / OCI')
            content['crossComponentResources']=[WORKSPACE]
        if item.get('name')=='ninjasec-oci-network-audit':
            content['title']='OCI Audit · eventos de las últimas 24 horas'
            content['query']='NINJASECMulticloudAudit() | where Provider == "OCI" and TimeGenerated > ago(24h) | project TimeGenerated, TimestampOrigin, EventName, Identity, Region, ResourceId, ResponseStatus, EventId | order by TimeGenerated desc | take 100'+DISPLAY_UTC
    data['items'].extend([
        {'type':1,'name':'ninjasec-multicloud-notice','content':{'json':'## Cumplimiento multicloud · AWS y OCI → Azure\nExportación periódica, no streaming. Tablas en UTC (sufijo Z); gráficos en zona del portal. La consulta prioriza OriginalEventTime (ISO UTC original); Azure puede sustituir su TimeGenerated nativo en relecturas de más de dos días. TimestampOrigin distingue fuente verificada y datos heredados. El estado compara última ingesta y último evento por separado; reingresar historia no demuestra actividad reciente. SIN DATOS y datos antiguos se muestran explícitamente. La continuidad de AWS al finalizar Academy sigue pendiente en K2.3. Las filas anteriores al enriquecimiento pueden carecer de identidad y fecha fuente verificada.'}},
        query_item('ninjasec-multicloud-freshness','Fuentes · antigüedad real de eventos e ingesta',FRESHNESS,30),
        query_item('ninjasec-multicloud-volume','Eventos únicos · 24 h (zona horaria del portal)','NINJASECMulticloudAudit() | where TimeGenerated > ago(24h) | summarize Eventos=count() by bin(TimeGenerated,1h), Provider | order by TimeGenerated asc',visualization='timechart'),
        query_item('ninjasec-multicloud-forensic','Cambios de seguridad y red · últimas 24 h',FORENSIC+DISPLAY_UTC),
        query_item('ninjasec-multicloud-history','Cambios de seguridad y red · histórico retenido (30 días)',FORENSIC.replace('ago(24h)','ago(30d)')+' | take 200'+DISPLAY_UTC,30)
    ])
    order=['texto - 2','ninjasec-multicloud-notice','ninjasec-multicloud-freshness','ninjasec-multicloud-volume','ninjasec-multicloud-forensic','ninjasec-multicloud-history']
    data['items']=sorted(data['items'],key=lambda item:order.index(item['name']) if item.get('name') in order else len(order))
    search={'type':'Microsoft.OperationalInsights/workspaces/savedSearches','apiVersion':'2020-08-01','name':'ninjasec-law/NINJASECMulticloudAudit',
        'properties':{'category':'NINJA-SEC','displayName':'AWS and OCI audit deduplicated by provider and eventID','functionAlias':'NINJASECMulticloudAudit','query':UNIFIED,'version':1}}
    forensics={'type':'Microsoft.OperationalInsights/workspaces/savedSearches','apiVersion':'2020-08-01','name':'ninjasec-law/NINJASECNetworkForensics',
        'dependsOn':["[resourceId('Microsoft.OperationalInsights/workspaces/savedSearches', 'ninjasec-law', 'NINJASECMulticloudAudit')]"],
        'properties':{'category':'NINJA-SEC','displayName':'Network security changes in AWS and OCI over 24h','functionAlias':'NINJASECNetworkForensics','query':FORENSIC,'version':1}}
    properties={k:v for k,v in workbook['properties'].items() if k in ['displayName','category','description','sourceId','version','tags']}
    properties['serializedData']=json.dumps(data,ensure_ascii=False)
    workbook_resource={'type':'Microsoft.Insights/workbooks','apiVersion':'2023-06-01','name':workbook['name'],'location':workbook['location'],'kind':'shared','properties':properties,'tags':workbook.get('tags',{}),
        'dependsOn':["[resourceId('Microsoft.OperationalInsights/workspaces/savedSearches', 'ninjasec-law', 'NINJASECMulticloudAudit')]"]}
    template={'$schema':'https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#','contentVersion':'1.0.0.0','resources':[table_resource,dcr_resource,search,forensics,workbook_resource]}
    path=Path('azure/compliance-forensics.json');path.write_text(json.dumps(template,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    az('deployment','group','create','-g','rg-ninjasec-compliance','-n','ninjasec-compliance-forensics','--template-file',str(path))
    for name,source in [('Publish-OciAudit','scripts/publish-oci-audit.ps1'),('Import-AwsAudit','scripts/import-aws-audit.ps1')]:
        arm('PUT',AUTOMATION+'/runbooks/'+name+'/draft/content','2023-11-01',Path(source).read_text(),True)
        arm('POST',AUTOMATION+'/runbooks/'+name+'/publish','2023-11-01',{})
    print('FORENSIC_SCHEMA_FUNCTIONS_WORKBOOK_AND_RUNBOOKS_DEPLOYED')

if __name__=='__main__':main()
