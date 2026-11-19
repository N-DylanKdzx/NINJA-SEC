"""Export a bounded CloudWatch CPU snapshot using the publisher's EC2 role."""

import datetime as dt
import json
import subprocess
import urllib.request


REGION = 'us-east-1'
SECRET = 'ninjasec/aws/cloudwatch-snapshot-writer'


def aws(*args):
    result = subprocess.run(['aws', *args, '--region', REGION, '--output', 'json', '--no-cli-pager'],
                            capture_output=True, text=True, timeout=22)
    if result.returncode:
        raise RuntimeError(f'AWS {args[0]} {args[1]} failed')
    return json.loads(result.stdout)


def main():
    now = dt.datetime.now(dt.timezone.utc)
    group = aws('autoscaling', 'describe-auto-scaling-groups', '--auto-scaling-group-names',
                'ninjasec-app')['AutoScalingGroups'][0]
    points = []
    for node in group['Instances']:
        if node['LifecycleState'] != 'InService':
            continue
        iid = node['InstanceId']
        result = aws('cloudwatch', 'get-metric-statistics', '--namespace', 'AWS/EC2',
                     '--metric-name', 'CPUUtilization', '--dimensions', f'Name=InstanceId,Value={iid}',
                     '--start-time', (now - dt.timedelta(minutes=30)).isoformat(),
                     '--end-time', now.isoformat(), '--period', '300', '--statistics', 'Average')
        for point in result['Datapoints']:
            timestamp = dt.datetime.fromisoformat(point['Timestamp'].replace('Z', '+00:00'))
            if now - dt.timedelta(minutes=15) <= timestamp <= now:
                points.append({'instance': iid, 'timestamp': timestamp.isoformat(), 'cpu_percent': point['Average']})
    if not points:
        raise RuntimeError('CloudWatch returned no fresh CPU samples')
    body = json.dumps({'source': 'AWS/EC2 CPUUtilization', 'generated_at': now.isoformat(), 'points': points}).encode()
    url = aws('secretsmanager', 'get-secret-value', '--secret-id', SECRET)['SecretString']
    req = urllib.request.Request(url, data=body, method='PUT', headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status not in (200, 201):
                raise RuntimeError('Object upload not accepted')
    except OSError:
        raise RuntimeError('Object upload failed') from None
    print(f'Published {len(points)} fresh CloudWatch samples')


if __name__ == '__main__':
    main()
