"""Merge OCI private routes and explicit MySQL rules; preserve existing entries."""
import oci
from pathlib import Path
import importlib.util

from importlib.machinery import SourceFileLoader
peer=SourceFileLoader('wg_peer',str(Path(__file__).with_name('prepare-wireguard-oci.py'))).load_module()

def main():
    cfg=oci.config.from_file(profile_name='NINJA_SEC_TERRAFORM');net=oci.core.VirtualNetworkClient(cfg)
    group=next(g for g in oci.pagination.list_call_get_all_results(net.list_network_security_groups,compartment_id=cfg['tenancy'],vcn_id=peer.VCN).data if g.display_name=='ninjasec-wireguard-utility')
    database='ocid1.networksecuritygroup.oc1.iad.aaaaaaaa7v5eg3u4tm27tsi5megq23abmfrh2lmokev2bxj2pjdko5jgj33a'
    def allow(group_id,direction,cidr,label):
        existing=oci.pagination.list_call_get_all_results(net.list_network_security_group_security_rules,group_id).data
        if any(r.description==label for r in existing):return
        kw=dict(direction=direction,protocol='6',is_stateless=False,description=label,tcp_options=oci.core.models.TcpOptions(destination_port_range=oci.core.models.PortRange(min=3306,max=3306)))
        kw.update({'source':cidr,'source_type':'CIDR_BLOCK'} if direction=='INGRESS' else {'destination':cidr,'destination_type':'CIDR_BLOCK'})
        net.add_network_security_group_security_rules(group_id,oci.core.models.AddNetworkSecurityGroupSecurityRulesDetails(security_rules=[oci.core.models.AddSecurityRuleDetails(**kw)]))
    for index,cidr in enumerate(['10.10.10.0/24','10.10.11.0/24']):
        allow(group.id,'INGRESS',cidr,'AWS APP private MySQL '+str(index))
        allow(database,'INGRESS',cidr,'AWS APP private MySQL '+str(index))
    allow(group.id,'INGRESS','10.20.10.191/32','HeatWave initiates private replication')
    allow(group.id,'EGRESS','10.20.10.191/32','Forward AWS APP to HeatWave')
    for index,cidr in enumerate(['10.10.20.0/24','10.10.21.0/24']):
        allow(group.id,'EGRESS',cidr,'Forward HeatWave to AWS DB '+str(index))
        allow(database,'EGRESS',cidr,'HeatWave to AWS DB '+str(index))
    spec=importlib.util.spec_from_file_location('wgssh',Path(__file__).with_name('wireguard-oci-ssh.py'));ssh=importlib.util.module_from_spec(spec);spec.loader.exec_module(ssh)
    print(ssh.run('sudo -n bash -s',Path(__file__).with_name('configure-wireguard-oci.sh').read_bytes()))
    response=net.get_vnic(peer.VNIC)
    net.update_vnic(peer.VNIC,oci.core.models.UpdateVnicDetails(skip_source_dest_check=True),if_match=response.headers['etag'])
    private=next(p for p in net.list_private_ips(vnic_id=peer.VNIC).data if p.is_primary)
    rt='ocid1.routetable.oc1.iad.aaaaaaaaarjku7swwx34c6t7a3mfmw7ly3dwomacvzklkrfz2rrshcl35iiq'
    response=net.get_route_table(rt);routes=response.data.route_rules
    existing=next((r for r in routes if r.destination=='10.10.0.0/16'),None)
    if existing and existing.network_entity_id!=private.id:
        previous='ocid1.privateip.oc1.iad.abuwcljttj4ea34hoemt5ixtwv6gxqiiwhm3opu2jpihaadkxsknd7meopza'
        if existing.network_entity_id!=previous:raise RuntimeError('Existing AWS route uses an unrecognized next hop; manual review required')
        existing.network_entity_id=private.id
        net.update_route_table(rt,oci.core.models.UpdateRouteTableDetails(route_rules=routes),if_match=response.headers['etag'])
    if not existing:
        routes.append(oci.core.models.RouteRule(destination='10.10.0.0/16',destination_type='CIDR_BLOCK',network_entity_id=private.id,description='AWS via private utility WireGuard peer; no DRG'))
        net.update_route_table(rt,oci.core.models.UpdateRouteTableDetails(route_rules=routes),if_match=response.headers['etag'])
    print('OCI_RETURN_ROUTE',rt,'10.10.0.0/16',private.id)

if __name__=='__main__':main()
