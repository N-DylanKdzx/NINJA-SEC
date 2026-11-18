"""Configure the approved private utility peer without changing VCN routes."""
import importlib.util
import json
from pathlib import Path
import oci

VCN='ocid1.vcn.oc1.iad.amaaaaaa3nxgmgaaxc45vda6zodcagfq2sa2uliasla75ray67di4t4gtqca'
VNIC='ocid1.vnic.oc1.iad.abuwcljtcffp4wa4iyt3s6zepz437qgbi2efcysbxel5m4rotnh7xhleayeq'

def main():
    cfg=oci.config.from_file(profile_name='NINJA_SEC_TERRAFORM')
    net=oci.core.VirtualNetworkClient(cfg)
    groups=oci.pagination.list_call_get_all_results(net.list_network_security_groups,compartment_id=cfg['tenancy'],vcn_id=VCN).data
    group=next((g for g in groups if g.display_name=='ninjasec-wireguard-utility'),None)
    if group is None:
        group=net.create_network_security_group(oci.core.models.CreateNetworkSecurityGroupDetails(compartment_id=cfg['tenancy'],vcn_id=VCN,display_name='ninjasec-wireguard-utility')).data
    rules=oci.pagination.list_call_get_all_results(net.list_network_security_group_security_rules,group.id).data
    if not any(r.description=='WireGuard to existing AWS router only' for r in rules):
        net.add_network_security_group_security_rules(group.id,oci.core.models.AddNetworkSecurityGroupSecurityRulesDetails(security_rules=[oci.core.models.AddSecurityRuleDetails(direction='EGRESS',protocol='17',destination='52.5.105.205/32',destination_type='CIDR_BLOCK',is_stateless=False,description='WireGuard to existing AWS router only',udp_options=oci.core.models.UdpOptions(destination_port_range=oci.core.models.PortRange(min=51820,max=51820)))]))
    vnic=net.get_vnic(VNIC).data
    if group.id not in vnic.nsg_ids:
        net.update_vnic(VNIC,oci.core.models.UpdateVnicDetails(nsg_ids=vnic.nsg_ids+[group.id]))
    spec=importlib.util.spec_from_file_location('wgssh',Path(__file__).with_name('wireguard-oci-ssh.py'))
    ssh=importlib.util.module_from_spec(spec);spec.loader.exec_module(ssh)
    keys=json.loads(Path('E:/NINJA-SEC/Credenciales de Acceso/ninjasec-wireguard.json').read_text())
    config=('[Interface]\nAddress = 10.255.254.2/30\nListenPort = 51820\nMTU = 1380\nPrivateKey = '+keys['oci']['private']+'\n\n[Peer]\nPublicKey = '+keys['aws']['public']+'\nAllowedIPs = 10.255.254.1/32, 10.10.0.0/16\nEndpoint = 52.5.105.205:51820\nPersistentKeepalive = 25\n')
    ssh.run("sudo -n sh -c 'umask 077; cat > /etc/wireguard/wg0.conf'",config.encode())
    commands='''set -eu
firewall-cmd --permanent --get-zones | tr ' ' '\\n' | grep -qx ninjasec-wg || firewall-cmd --permanent --new-zone=ninjasec-wg
firewall-cmd --permanent --zone=ninjasec-wg --set-target=DROP
firewall-cmd --permanent --zone=ninjasec-wg --add-interface=wg0
firewall-cmd --permanent --zone=ninjasec-wg --add-rich-rule='rule family="ipv4" source address="10.255.254.1/32" protocol value="icmp" accept'
firewall-cmd --reload
systemctl enable --now wg-quick@wg0
sleep 3
/usr/local/bin/wg show wg0
ping -c 3 -W 3 10.255.254.1
free -m
curl -s -o /dev/null -w 'PORTAL_HTTP=%{http_code}\\n' http://127.0.0.1:8080/
'''
    print('OCI_WG_NSG',group.id,flush=True)
    print(json.dumps(ssh.run('sudo -n bash -s',commands.encode(),60)))

if __name__=='__main__':main()
