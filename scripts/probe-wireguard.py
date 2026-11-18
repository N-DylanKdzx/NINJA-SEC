"""Check existing AWS/OCI routers and obtain a short-lived private SSH path."""
import json
import os
from pathlib import Path
import ssl
import subprocess
import time
import urllib.request

import boto3
import oci

ROOT = Path('E:/NINJA-SEC/Credenciales de Acceso')
BASTION = 'ocid1.bastion.oc1.iad.amaaaaaa3nxgmgaaa6fbn3e4bcmrbb2akgog6jawbjgnoyhdamlgiyznfnwq'
INSTANCE = 'ocid1.instance.oc1.iad.anuwcljt3nxgmgacy6ljbmb5iateotxlcnh5x4hl43o3ywricnav6kav3qla'
KNOWN_HOSTS = 'C:/Users/DYLAN/.ssh/ninjasec_oci_known_hosts'

def ssh_command(session_id, command):
    proxy = ('ssh -i C:/Users/DYLAN/.ssh/ninjasec_oci_bastion_rsa '
             '-o BatchMode=yes -o StrictHostKeyChecking=accept-new '
             '-o UserKnownHostsFile='+KNOWN_HOSTS+' -W %h:%p -p 22 '+session_id+
             '@host.bastion.us-ashburn-1.oci.oraclecloud.com')
    return ['ssh','-i','C:/Users/DYLAN/.ssh/ninjasec_oci_ed25519','-o','BatchMode=yes',
            '-o','ConnectTimeout=25','-o','StrictHostKeyChecking=accept-new',
            '-o','UserKnownHostsFile='+KNOWN_HOSTS,'-o','ProxyCommand='+proxy,
            'opc@10.20.10.212',command]

def main():
    cfg=oci.config.from_file(profile_name='NINJA_SEC_TERRAFORM')
    network=oci.core.VirtualNetworkClient(cfg)
    compute=oci.core.ComputeClient(cfg)
    instance=compute.get_instance(INSTANCE).data
    print('OCI_INSTANCE',instance.display_name,instance.shape,instance.lifecycle_state,flush=True)
    for attachment in compute.list_vnic_attachments(cfg['tenancy'],instance_id=INSTANCE).data:
        vnic=network.get_vnic(attachment.vnic_id).data
        print('OCI_VNIC',json.dumps({'id':vnic.id,'privateIp':vnic.private_ip,'publicIp':vnic.public_ip,'nsgIds':vnic.nsg_ids,'skipSourceDestCheck':vnic.skip_source_dest_check}),flush=True)
    context=ssl.create_default_context(cafile=os.environ['REQUESTS_CA_BUNDLE'])
    with urllib.request.urlopen('https://checkip.amazonaws.com',context=context,timeout=15) as response:ip=response.read().decode().strip()
    client=oci.bastion.BastionClient(cfg)
    bastion=client.get_bastion(BASTION).data
    if ip+'/32' not in bastion.client_cidr_block_allow_list:
        raise RuntimeError('Bastion does not authorize current client IP; review /32 allowlist before connecting')
    public=subprocess.run(['ssh-keygen','-y','-f','C:/Users/DYLAN/.ssh/ninjasec_oci_bastion_rsa'],capture_output=True,text=True,check=True).stdout.strip()
    target=oci.bastion.models.CreatePortForwardingSessionTargetResourceDetails(target_resource_private_ip_address='10.20.10.212',target_resource_port=22)
    details=oci.bastion.models.CreateSessionDetails(bastion_id=BASTION,target_resource_details=target,key_details=oci.bastion.models.PublicKeyDetails(public_key_content=public),display_name='ninjasec-wireguard-setup',session_ttl_in_seconds=1800)
    session=client.create_session(details).data
    for attempt in range(30):
        session=client.get_session(session.id).data
        if session.lifecycle_state=='ACTIVE':break
        if session.lifecycle_state in ('FAILED','DELETED'):raise RuntimeError('Bastion session failed')
        time.sleep(2)
    else:raise RuntimeError('Bastion activation timed out')
    ROOT.joinpath('oci-wireguard-session.json').write_text(json.dumps({'sessionId':session.id,'privateIp':'10.20.10.212','instanceId':INSTANCE}),encoding='utf-8')
    result=subprocess.run(ssh_command(session.id,"hostname; uname -r; free -m; df -h /; command -v wg || true; sudo -n systemctl --failed --no-pager"),capture_output=True,text=True,timeout=60)
    print('OCI_SSH_PROBE',result.returncode,result.stdout,result.stderr,flush=True)
    if result.returncode:raise RuntimeError('Private OCI SSH probe failed')
    aws=boto3.Session(profile_name='ninjasec-academy-194766',region_name='us-east-1').client('ssm')
    command=aws.send_command(InstanceIds=['i-0e3a000a38a35f248'],DocumentName='AWS-RunShellScript',Parameters={'commands':['uname -r','free -m','df -h /','command -v wg || true','sysctl -n net.ipv4.ip_forward']},Comment='NINJA-SEC M1 router capacity and WireGuard probe')['Command']['CommandId']
    for attempt in range(40):
        try:
            result=aws.get_command_invocation(CommandId=command,InstanceId='i-0e3a000a38a35f248')
            if result['Status'] in ('Success','Failed','Cancelled','TimedOut'):break
        except aws.exceptions.InvocationDoesNotExist:pass
        time.sleep(2)
    print('AWS_PROBE',command,result['Status'],result['StandardOutputContent'],result['StandardErrorContent'],flush=True)

if __name__=='__main__':main()
