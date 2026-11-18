"""Export real CloudTrail objects to Azure WORM; checkpoint after upload only."""
import datetime as dt
import hashlib
import importlib.util
import json
import os
import uuid
import urllib.request
import urllib.error
import boto3
from botocore.config import Config

spec = importlib.util.spec_from_file_location('reader', os.path.join(os.path.dirname(__file__), 'read-cloudtrail.py'))
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)

def handler(event, context):
    s3 = boto3.client('s3', config=Config(signature_version='s3v4', s3={'us_east_1_regional_endpoint':'regional'}))
    bucket = os.environ['AUDIT_BUCKET']
    if event.get('HealthCheck'):
        latest = None
        for page in s3.get_paginator('list_objects_v2').paginate(Bucket=bucket, Prefix='export-state/batches/'):
            for item in page.get('Contents', []):
                latest = max(latest, item['LastModified']) if latest else item['LastModified']
        age = (dt.datetime.now(dt.timezone.utc)-latest).total_seconds()/3600 if latest else 9999
        boto3.client('cloudwatch').put_metric_data(Namespace='NINJA-SEC/Audit',MetricData=[{'MetricName':'AzureIngestionAgeHours','Value':age,'Unit':'None'}])
        receiver = json.loads(boto3.client('secretsmanager').get_secret_value(SecretId=os.environ['AZURE_SECRET_ARN'])['SecretString'])
        remaining = (dt.datetime.fromisoformat(receiver['expiresAt'])-dt.datetime.now(dt.timezone.utc)).total_seconds()/86400
        boto3.client('cloudwatch').put_metric_data(Namespace='NINJA-SEC/Audit',MetricData=[{'MetricName':'AzureReceiverExpiryDays','Value':remaining,'Unit':'None'}])
        return {'ageHours':round(age,3),'hasAcknowledgement':bool(latest),'receiverExpiryDays':round(remaining,2)}
    prefix = 'AWSLogs/' + os.environ['ACCOUNT_ID'] + '/CloudTrail/'
    target = json.loads(boto3.client('secretsmanager').get_secret_value(SecretId=os.environ['AZURE_SECRET_ARN'])['SecretString'])
    if event.get('Key'):
        if not event['Key'].startswith(prefix) or not event['Key'].endswith('.json.gz'):
            raise ValueError('Key outside CloudTrail prefix')
        keys = [event['Key']]
    else:
        days = {(dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=n)).strftime('/%Y/%m/%d/') for n in range(3)}
        keys = [k for k in reader.object_keys(s3, bucket, [], prefix) if any(day in k for day in days)]
    pending = []
    skipped = 0
    for key in keys:
        head = s3.head_object(Bucket=bucket, Key=key)
        marker = 'export-state/' + hashlib.sha256((key + head['ETag']).encode()).hexdigest() + '.json'
        try:
            s3.head_object(Bucket=bucket, Key=marker)
            if event.get('Replay') and event.get('Key'):
                pending.append((key, marker))
            else:
                skipped += 1
        except s3.exceptions.ClientError as exc:
            if exc.response['Error']['Code'] not in ('404', 'NoSuchKey', 'NotFound'):
                raise
            pending.append((key, marker))
    if not pending:
        result = {'uploaded':0,'skipped':skipped,'records':0}
        print(json.dumps(result))
        return result
    batch = reader.read_batch(s3, bucket, [key for key, marker in pending])
    body = reader.canonical_bytes(batch)
    sha = hashlib.sha256(body).hexdigest()
    blob = 'aws-audit-' + sha + '.json'
    stage = 'export-batches/' + sha + '.json'
    ack = 'export-state/batches/' + sha + '-' + str(uuid.uuid4()) + '.json'
    s3.put_object(Bucket=bucket, Key=stage, Body=body, ContentType='application/json')
    delivery = {'blob':blob,
        'sourceUrl':s3.generate_presigned_url('get_object', Params={'Bucket':bucket,'Key':stage},ExpiresIn=1800),
        'ackUrl':s3.generate_presigned_url('put_object', Params={'Bucket':bucket,'Key':ack,'ContentType':'application/json'},ExpiresIn=1800)}
    request = urllib.request.Request(target['webhookUrl'], data=reader.canonical_bytes(delivery), method='POST', headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            if response.status != 202:
                raise RuntimeError('Azure receiver did not accept delivery')
    except urllib.error.HTTPError as exc:
        raise RuntimeError('Azure receiver HTTP ' + str(exc.code)) from None
    import time
    deadline = time.monotonic() + min(600, context.get_remaining_time_in_millis()/1000 - 30)
    while time.monotonic() < deadline:
        try:
            response = s3.get_object(Bucket=bucket,Key=ack)
            confirmation = json.loads(response['Body'].read())
            if confirmation.get('sha256') != sha or confirmation.get('blob') != blob or confirmation.get('recordCount') != len(batch['Records']):
                raise RuntimeError('Invalid Azure acknowledgement')
            break
        except s3.exceptions.ClientError as exc:
            if exc.response['Error']['Code'] not in ('404','NoSuchKey','NotFound'):
                raise
        time.sleep(10)
    else:
        raise RuntimeError('Azure archive/ingestion acknowledgement timed out; retry remains pending')
    for key, marker in pending:
        s3.put_object(Bucket=bucket,Key=marker,Body=reader.canonical_bytes({'blob':blob,'sha256':sha,'source':key}),ContentType='application/json')
    result = {'uploaded':len(pending),'skipped':skipped,'records':len(batch['Records']),'blob':blob}
    print(json.dumps(result))
    return result
