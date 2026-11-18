"""Stage reversible 4-GiB OCI peers within the approved USD 8/14-day CPU+RAM budget.

Original instances/disks remain intact. This script does not switch LB backends
or WireGuard routes. The new instances have WireGuard disabled until cutover.
"""
import argparse
import base64
import importlib.util
from pathlib import Path
import time
import oci

AD='meXg:US-ASHBURN-AD-3'
SUBNET='ocid1.subnet.oc1.iad.aaaaaaaazpxp43ofolxis2j6cawsqajxpzqtezchvqpbqjii25ojl3lwv4rq'
SOURCES={
    'utility':('ocid1.instance.oc1.iad.anuwcljt3nxgmgacays7ij4hje7tqwebsgo6wm3mkpwy2cl3veji2ncwaaea','10.20.10.40'),
    'replica':('ocid1.instance.oc1.iad.anuwcljt3nxgmgacy6ljbmb5iateotxlcnh5x4hl43o3ywricnav6kav3qla','10.20.10.41'),
}

def wait_volume(client,id):
    for _ in range(90):
        volume=client.get_boot_volume(id).data
        if volume.lifecycle_state=='AVAILABLE':return volume
        if volume.lifecycle_state in ('FAULTY','TERMINATED'):raise RuntimeError('Boot clone failed')
        time.sleep(3)
    raise RuntimeError('Boot clone still pending; rerun safely after checking state')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('host',choices=SOURCES);args=parser.parse_args()
    cfg=oci.config.from_file(profile_name='NINJA_SEC_TERRAFORM')
    co=oci.core.ComputeClient(cfg);bs=oci.core.BlockstorageClient(cfg);net=oci.core.VirtualNetworkClient(cfg)
    original,ip=SOURCES[args.host];source=co.get_instance(original).data
    name='ninjasec-'+args.host+'-stable-01'
    subnet=net.get_subnet(SUBNET).data
    for security_list_id in subnet.security_list_ids:
        response=net.get_security_list(security_list_id);rules=response.data.egress_security_rules
        if not any(r.destination==ip+'/32' and r.protocol=='6' and r.tcp_options and r.tcp_options.destination_port_range.min==22 for r in rules):
            rules.append(oci.core.models.EgressSecurityRule(destination=ip+'/32',destination_type='CIDR_BLOCK',protocol='6',is_stateless=False,description='Bastion to staged memory-stable host SSH only',tcp_options=oci.core.models.TcpOptions(destination_port_range=oci.core.models.PortRange(min=22,max=22))))
            net.update_security_list(security_list_id,oci.core.models.UpdateSecurityListDetails(egress_security_rules=rules),if_match=response.headers['etag'])
    existing=oci.pagination.list_call_get_all_results(co.list_instances,cfg['tenancy']).data
    found=next((x for x in existing if x.display_name==name and x.lifecycle_state!='TERMINATED'),None)
    if found:
        print('EXISTING_INSTANCE',name,found.id,found.lifecycle_state,flush=True);return
    source_vnic=net.get_vnic(co.list_vnic_attachments(cfg['tenancy'],instance_id=original).data[0].vnic_id).data
    used=[p.ip_address for p in net.list_private_ips(subnet_id=SUBNET).data]
    if ip in used:raise RuntimeError('Requested staging IP is already allocated')
    volumes=oci.pagination.list_call_get_all_results(bs.list_boot_volumes,availability_domain=AD,compartment_id=cfg['tenancy']).data
    clone=next((v for v in volumes if v.display_name==name+'-boot' and v.lifecycle_state!='TERMINATED'),None)
    if clone is None:
        total=sum(v.size_in_gbs for v in volumes if v.lifecycle_state!='TERMINATED')
        blocks=oci.pagination.list_call_get_all_results(bs.list_volumes,compartment_id=cfg['tenancy']).data
        total+=sum(v.size_in_gbs for v in blocks if v.lifecycle_state!='TERMINATED')
        boot=co.list_boot_volume_attachments(AD,cfg['tenancy'],instance_id=original).data[0].boot_volume_id
        size=bs.get_boot_volume(boot).data.size_in_gbs
        if total+size>200:raise RuntimeError('Would exceed the verified 200-GiB storage envelope')
        ssh=None
        if args.host=='utility':
            spec=importlib.util.spec_from_file_location('wgssh',Path(__file__).with_name('wireguard-oci-ssh.py'));ssh=importlib.util.module_from_spec(spec);spec.loader.exec_module(ssh)
            ssh.run('sudo -n systemctl disable wg-quick@wg0; sync',host='10.20.10.36')
        try:
            clone=bs.create_boot_volume(oci.core.models.CreateBootVolumeDetails(availability_domain=AD,compartment_id=cfg['tenancy'],display_name=name+'-boot',vpus_per_gb=10,source_details=oci.core.models.BootVolumeSourceFromBootVolumeDetails(type='bootVolume',id=boot))).data
            print('BOOT_CLONE',clone.id,flush=True)
            clone=wait_volume(bs,clone.id)
        finally:
            if ssh:print('ORIGINAL_WG_ENABLED',ssh.run('sudo -n systemctl enable wg-quick@wg0',host='10.20.10.36').strip(),flush=True)
    else:clone=wait_volume(bs,clone.id)
    bootstrap='''#!/bin/bash
set -eu
systemctl disable --now wg-quick@wg0 2>/dev/null || true
systemctl disable --now dnf-makecache.timer 2>/dev/null || true
mkdir -p /etc/systemd/system/dnf-makecache.service.d
printf '[Service]\\nMemoryHigh=192M\\nMemoryMax=256M\\nMemorySwapMax=256M\\n' > /etc/systemd/system/dnf-makecache.service.d/memory.conf
systemctl daemon-reload
if systemctl is-active --quiet firewalld; then
 firewall-cmd --permanent --zone=public --add-rich-rule='rule family="ipv4" source address="10.20.10.105/32" port port="22" protocol="tcp" accept'
 firewall-cmd --reload
fi
systemctl enable --now sshd
systemctl restart sshd
'''
    metadata={'ssh_authorized_keys':source.metadata['ssh_authorized_keys'],'user_data':base64.b64encode(bootstrap.encode()).decode()}
    for shape in ['VM.Standard.E3.Flex','VM.Standard.E5.Flex']:
        try:
            result=co.launch_instance(oci.core.models.LaunchInstanceDetails(compartment_id=cfg['tenancy'],availability_domain=AD,display_name=name,shape=shape,shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(ocpus=1,memory_in_gbs=4,baseline_ocpu_utilization='BASELINE_1_8'),source_details=oci.core.models.InstanceSourceViaBootVolumeDetails(source_type='bootVolume',boot_volume_id=clone.id),create_vnic_details=oci.core.models.CreateVnicDetails(subnet_id=SUBNET,private_ip=ip,assign_public_ip=False,nsg_ids=source_vnic.nsg_ids),metadata=metadata,is_pv_encryption_in_transit_enabled=True,availability_config=oci.core.models.LaunchInstanceAvailabilityConfigDetails(recovery_action='RESTORE_INSTANCE'),freeform_tags={'Project':'NINJA-SEC','Purpose':'Memory stability migration','Budget':'CPU+RAM <= USD8 for two instances /14days'})).data
            print('STAGED_INSTANCE',name,result.id,shape,ip,result.lifecycle_state,flush=True)
            for _ in range(90):
                result=co.get_instance(result.id).data
                if result.lifecycle_state=='RUNNING':
                    print('RUNNING',result.id,result.shape_config,flush=True);return
                if result.lifecycle_state in ('TERMINATING','TERMINATED'):
                    raise RuntimeError('Asynchronous launch failed; inspect Work Request before retrying')
                time.sleep(3)
            raise RuntimeError('Still provisioning; inspect before retrying')
        except oci.exceptions.ServiceError as exc:
            print('LAUNCH_REJECTED',shape,exc.status,exc.code,exc.message,flush=True)
            if not (exc.status==500 and 'capacity' in exc.message.lower()):raise
    raise RuntimeError('No capacity; originals unchanged, boot clone retained')

if __name__=='__main__':main()
