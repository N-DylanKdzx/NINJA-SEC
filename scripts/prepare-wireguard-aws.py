"""Prepare the existing router; private keys remain local and in SecureString.

This stage deliberately does not install cross-cloud routes before OCI is ready.
"""
import base64
import json
import os
from pathlib import Path
import subprocess
import time

import boto3
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives import serialization

ROOT = Path('E:/NINJA-SEC/Credenciales de Acceso')
ROUTER = 'i-0e3a000a38a35f248'

def keypair():
    key = X25519PrivateKey.generate()
    encode = lambda value: base64.b64encode(value).decode('ascii')
    return {'private': encode(key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())),
            'public': encode(key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))}

def main():
    session = boto3.Session(profile_name='ninjasec-academy-194766', region_name='us-east-1')
    if session.client('sts').get_caller_identity()['Account'] != '533267256700':
        raise RuntimeError('Unexpected AWS account')
    path = ROOT / 'ninjasec-wireguard.json'
    if not path.exists():
        # Create the empty file and restrict it BEFORE writing any key material.
        path.touch(exist_ok=False)
        subprocess.run(['icacls', str(path), '/inheritance:r', '/grant:r',
                        os.environ['USERDOMAIN']+'\\'+os.environ['USERNAME']+':F',
                        '*S-1-5-18:F', '*S-1-5-32-544:F'], check=True, capture_output=True)
        path.write_text(json.dumps({'aws':keypair(), 'oci':keypair()}, indent=2), encoding='utf-8')
    keys = json.loads(path.read_text(encoding='utf-8'))
    configuration = ('[Interface]\nAddress = 10.255.254.1/30\nListenPort = 51820\n'
                     'MTU = 1380\nPrivateKey = '+keys['aws']['private']+'\n\n[Peer]\n'
                     'PublicKey = '+keys['oci']['public']+'\n'
                     'AllowedIPs = 10.255.254.2/32, 10.20.0.0/16\n')
    ssm = session.client('ssm')
    ssm.put_parameter(Name='/ninjasec/wireguard/aws', Type='SecureString', Tier='Standard',
                      KeyId='d298d19a-46c6-4fd6-bbde-df3e59bce700',
                      Value=configuration, Overwrite=True,
                      Description='Existing AWS router WireGuard configuration; private key; never log value')
    commands = [
        'set -eu',
        'install -d -m 700 /etc/wireguard',
        'umask 077',
        'aws ssm get-parameter --name /ninjasec/wireguard/aws --with-decryption --region us-east-1 --query Parameter.Value --output text > /etc/wireguard/wg0.conf',
        'chmod 600 /etc/wireguard/wg0.conf',
        'modprobe wireguard',
        # Do not start/enable the service until OCI and the perimeter are ready.
        'wg-quick strip wg0 >/dev/null',
        'stat -c "%a %U %n" /etc/wireguard /etc/wireguard/wg0.conf',
        'wg --version',
        'printf "Configuration validated; service activation awaits OCI peer.\\n"',
    ]
    command = ssm.send_command(InstanceIds=[ROUTER], DocumentName='AWS-RunShellScript',
                              Parameters={'commands':commands}, Comment='NINJA-SEC M1 protected AWS WireGuard preparation')['Command']['CommandId']
    print('COMMAND_ID', command, flush=True)
    for _ in range(30):
        try:
            result=ssm.get_command_invocation(CommandId=command, InstanceId=ROUTER)
            if result['Status'] in ('Success','Failed','Cancelled','TimedOut'):
                print(result['Status'], result['StandardOutputContent'], result['StandardErrorContent'], flush=True)
                if result['Status']!='Success': raise RuntimeError('Preparation failed')
                return
        except ssm.exceptions.InvocationDoesNotExist:
            pass
        time.sleep(2)
    raise RuntimeError('Command still running; inspect command ID')

if __name__ == '__main__':
    main()
