"""Deploy audit exporter using existing LabRole; secrets stay outside the repository."""
import datetime as dt
import io
import json
import os
from pathlib import Path
import subprocess
import zipfile
import boto3

def az(*args):
    result = subprocess.run(['C:/Program Files/Microsoft SDKs/Azure/CLI2/wbin/az.cmd',*args,'-o','json'],capture_output=True,text=True)
    if result.returncode:
        raise RuntimeError(result.stderr[:1800])
    return json.loads(result.stdout) if result.stdout.strip() else None

def main():
    session=boto3.Session(profile_name='ninjasec-academy-194766',region_name='us-east-1')
    account=session.client('sts').get_caller_identity()['Account']
    if account!='533267256700': raise RuntimeError('Unexpected AWS account')
    secrets=session.client('secretsmanager')
    name='ninjasec/azure-audit-writer'
    secret=secrets.describe_secret(SecretId=name)
    receiver=json.loads(secrets.get_secret_value(SecretId=name)['SecretString'])
    if 'webhookUrl' not in receiver:
        raise RuntimeError('Publish the Azure managed-identity receiver first')
    archive=io.BytesIO()
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        z.write('scripts/export-cloudtrail-lambda.py','exporter.py')
        z.write('scripts/read-cloudtrail.py','read-cloudtrail.py')
    client=session.client('lambda'); function='ninjasec-export-cloudtrail'
    configuration=dict(FunctionName=function,Role=f'arn:aws:iam::{account}:role/LabRole',Runtime='python3.12',Handler='exporter.handler',Timeout=900,MemorySize=256,Environment={'Variables':{'AUDIT_BUCKET':f'ninjasec-audit-{account}','ACCOUNT_ID':account,'AZURE_SECRET_ARN':secret['ARN']}})
    try:
        client.get_function(FunctionName=function)
        client.update_function_code(FunctionName=function,ZipFile=archive.getvalue())
        client.get_waiter('function_updated_v2').wait(FunctionName=function)
        client.update_function_configuration(**configuration)
    except client.exceptions.ResourceNotFoundException:
        client.create_function(**configuration,Code={'ZipFile':archive.getvalue()})
    client.get_waiter('function_active_v2').wait(FunctionName=function)
    events=session.client('events')
    rule=events.put_rule(Name='ninjasec-audit-daily',ScheduleExpression='cron(0 7 * * ? *)',State='ENABLED',Description='Daily 02:00 America/Bogota export; renews AWS credentials through Lambda role')
    try: client.add_permission(FunctionName=function,StatementId='DailyAuditSchedule',Action='lambda:InvokeFunction',Principal='events.amazonaws.com',SourceArn=rule['RuleArn'])
    except client.exceptions.ResourceConflictException: pass
    result=events.put_targets(Rule='ninjasec-audit-daily',Targets=[{'Id':'export','Arn':f'arn:aws:lambda:us-east-1:{account}:function:{function}'}])
    if result['FailedEntryCount']: raise RuntimeError('Schedule target rejected')
    session.client('cloudwatch').put_metric_alarm(AlarmName='ninjasec-audit-export-errors',Namespace='AWS/Lambda',MetricName='Errors',Dimensions=[{'Name':'FunctionName','Value':function}],Statistic='Sum',Period=300,EvaluationPeriods=1,Threshold=1,ComparisonOperator='GreaterThanOrEqualToThreshold',TreatMissingData='notBreaching',AlarmActions=[f'arn:aws:sns:us-east-1:{account}:ninjasec-monitoring-alerts'])
    health=events.put_rule(Name='ninjasec-audit-freshness',ScheduleExpression='rate(5 minutes)',State='ENABLED',Description='Check last Azure archive and ingestion acknowledgement')
    try: client.add_permission(FunctionName=function,StatementId='AuditFreshnessSchedule',Action='lambda:InvokeFunction',Principal='events.amazonaws.com',SourceArn=health['RuleArn'])
    except client.exceptions.ResourceConflictException: pass
    result=events.put_targets(Rule='ninjasec-audit-freshness',Targets=[{'Id':'health','Arn':f'arn:aws:lambda:us-east-1:{account}:function:{function}','Input':'{"HealthCheck":true}'}])
    if result['FailedEntryCount']: raise RuntimeError('Freshness target rejected')
    session.client('cloudwatch').put_metric_alarm(AlarmName='ninjasec-azure-audit-stale',Namespace='NINJA-SEC/Audit',MetricName='AzureIngestionAgeHours',Statistic='Maximum',Period=600,EvaluationPeriods=1,DatapointsToAlarm=1,Threshold=26,ComparisonOperator='GreaterThanOrEqualToThreshold',TreatMissingData='breaching',AlarmActions=[f'arn:aws:sns:us-east-1:{account}:ninjasec-monitoring-alerts'])
    session.client('cloudwatch').put_metric_alarm(AlarmName='ninjasec-azure-audit-receiver-expiry',Namespace='NINJA-SEC/Audit',MetricName='AzureReceiverExpiryDays',Statistic='Minimum',Period=600,EvaluationPeriods=1,Threshold=7,ComparisonOperator='LessThanOrEqualToThreshold',TreatMissingData='missing',AlarmActions=[f'arn:aws:sns:us-east-1:{account}:ninjasec-monitoring-alerts'])
    print(json.dumps({'function':function,'schedule':rule['RuleArn'],'secretArn':secret['ARN']}))

if __name__=='__main__': main()
