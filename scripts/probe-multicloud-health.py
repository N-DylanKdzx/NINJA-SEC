"""Collect independent read-only health signals and classify them without failover."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import ssl
import time
from urllib.error import HTTPError
from urllib.request import urlopen

import boto3
import oci


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def portal_health(url):
    context = ssl.create_default_context(cafile=os.environ.get('REQUESTS_CA_BUNDLE'))
    try:
        with urlopen(url, context=context, timeout=8) as response:
            return response.status == 200 and json.load(response)['status'] == 'ok'
    except (OSError, HTTPError):
        return False


def sql_health(ssm, instance):
    command = ssm.send_command(
        InstanceIds=[instance], DocumentName='AWS-RunShellScript', TimeoutSeconds=35,
        Parameters={'commands': ["curl -sS --max-time 8 -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/health"]},
    )['Command']['CommandId']
    for _ in range(15):
        time.sleep(2)
        try:
            result = ssm.get_command_invocation(CommandId=command, InstanceId=instance)
        except ssm.exceptions.InvocationDoesNotExist:
            continue
        if result['Status'] == 'Success':
            code = result['StandardOutputContent'].strip()
            return {'200': True, '503': False}.get(code)
        if result['Status'] not in ('Pending', 'InProgress', 'Delayed'):
            return None
    return None


def tunnel_health():
    ssh = load_script('wireguard-oci-ssh.py')
    code = b'''import subprocess
subprocess.run(['ping','-c','2','-W','2','10.255.254.1'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
r=subprocess.run(['/usr/local/bin/wg','show','wg0','latest-handshakes'],capture_output=True,text=True)
if r.returncode:
 link=subprocess.run(['ip','link','show','dev','wg0'],capture_output=True,text=True)
 if link.returncode and 'does not exist' in link.stderr:
  print(0)
  raise SystemExit(0)
 raise RuntimeError('Could not inspect WireGuard')
for line in r.stdout.splitlines():
 print(line.split()[-1])
'''
    ages = [time.time() - int(value) for value in ssh.run('sudo -n python3 -', data=code, timeout=40).split()]
    return any(0 <= age <= 180 for age in ages)


def measure(args):
    session = boto3.Session(region_name='us-east-1')
    channels = oci.mysql.ChannelsClient(oci.config.from_file(profile_name='NINJA_SEC_TERRAFORM'), timeout=(5, 15))

    def aws_access():
        try:
            return session.client('sts').get_caller_identity()['Account'] == '533267256700'
        except Exception:
            return False

    def channel_status():
        state = channels.get_channel(args.channel).data.lifecycle_state
        return {'ACTIVE': True, 'NEEDS_ATTENTION': False, 'INACTIVE': False, 'FAILED': False}.get(state)

    ssm = session.client('ssm')
    checks = {
        'aws_portal': lambda: portal_health('https://portal-aws.ninjasec.dev/health'),
        'aws_app_sql': lambda: sql_health(ssm, args.instance),
        'aws_management': aws_access,
        'wireguard': tunnel_health,
        'replication': channel_status,
    }
    errors = {}
    signals = {}
    with ThreadPoolExecutor(max_workers=len(checks)) as pool:
        tasks = {name: pool.submit(check) for name, check in checks.items()}
        for name, task in tasks.items():
            try:
                signals[name] = task.result()
            except Exception as error:
                signals[name] = None
                errors[name] = type(error).__name__
    classifier = load_script('classify-multicloud-health.py')
    return {'timestamp': datetime.now(timezone.utc).isoformat(), 'signals': signals,
            'errors': errors, 'classification': classifier.classify(signals),
            'promotion_authorized': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instance', required=True, help='Current private AWS application instance')
    parser.add_argument('--channel', required=True, help='OCI incidents replication channel OCID')
    parser.add_argument('--samples', type=int, default=1)
    parser.add_argument('--interval', type=int, default=60)
    args = parser.parse_args()
    if args.samples < 1 or args.interval < 30:
        parser.error('Require at least one sample and a minimum interval of 30 seconds')
    for i in range(args.samples):
        if i:
            time.sleep(args.interval)
        print(json.dumps(measure(args)), flush=True)


if __name__ == '__main__':
    main()
