"""Update dependent network/alarms after verified memory-host migration.

Original instances are retained; stopping them requires --stop-originals.
"""
import argparse
import oci

OLD_UTILITY='ocid1.instance.oc1.iad.anuwcljt3nxgmgacays7ij4hje7tqwebsgo6wm3mkpwy2cl3veji2ncwaaea'
OLD_REPLICA='ocid1.instance.oc1.iad.anuwcljt3nxgmgacy6ljbmb5iateotxlcnh5x4hl43o3ywricnav6kav3qla'
NEW_UTILITY='ocid1.instance.oc1.iad.anuwcljt3nxgmgac3gpot2j44ddf23mngyckjnq5qqae4va7xfibbjmlrutq'
NEW_REPLICA='ocid1.instance.oc1.iad.anuwcljt3nxgmgac6suofn76uki3a25nciwdev35fvk2xk6l6lbz36dsmlrq'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stop-originals',action='store_true');args=parser.parse_args()
    cfg=oci.config.from_file(profile_name='NINJA_SEC_TERRAFORM');monitor=oci.monitoring.MonitoringClient(cfg);net=oci.core.VirtualNetworkClient(cfg)
    for alarm in monitor.list_alarms(cfg['tenancy']).data:
        if not alarm.is_enabled:continue
        query=alarm.query.replace(OLD_UTILITY,NEW_UTILITY).replace(OLD_REPLICA,NEW_REPLICA)
        if query!=alarm.query:
            response=monitor.get_alarm(alarm.id)
            monitor.update_alarm(alarm.id,oci.monitoring.models.UpdateAlarmDetails(query=query),if_match=response.headers['etag'])
            print('MOVED_ENABLED_ALARM',alarm.display_name,alarm.id,flush=True)
    sl='ocid1.securitylist.oc1.iad.aaaaaaaafos4dac4dwneykh54t54dyj2lqo7ix6mt4rrxc3rxh57m5p7xweq'
    response=net.get_security_list(sl);rules=response.data.egress_security_rules
    for ip in ['10.20.10.40/32','10.20.10.41/32']:
        if not any(r.destination==ip and r.protocol=='6' and r.tcp_options and r.tcp_options.destination_port_range.min==22 for r in rules):
            rules.append(oci.core.models.EgressSecurityRule(destination=ip,destination_type='CIDR_BLOCK',protocol='6',is_stateless=False,description='Bastion to migrated host SSH only',tcp_options=oci.core.models.TcpOptions(destination_port_range=oci.core.models.PortRange(min=22,max=22))))
    net.update_security_list(sl,oci.core.models.UpdateSecurityListDetails(egress_security_rules=rules),if_match=response.headers['etag'])
    groups=[('ocid1.networksecuritygroup.oc1.iad.aaaaaaaanasaxkrlu4szysqwp37sz4hwj5hac2gvo27awryyxyfaaf4x5ipa','EGRESS','10.20.10.40/32',8080),('ocid1.networksecuritygroup.oc1.iad.aaaaaaaa7v5eg3u4tm27tsi5megq23abmfrh2lmokev2bxj2pjdko5jgj33a','INGRESS','10.20.10.40/32',3306),('ocid1.networksecuritygroup.oc1.iad.aaaaaaaa7v5eg3u4tm27tsi5megq23abmfrh2lmokev2bxj2pjdko5jgj33a','INGRESS','10.20.10.41/32',3306)]
    for id,direction,ip,port in groups:
        rules=net.list_network_security_group_security_rules(id).data
        if any(r.direction==direction and (r.source if direction=='INGRESS' else r.destination)==ip and r.tcp_options and r.tcp_options.destination_port_range.min==port for r in rules):continue
        kw=dict(direction=direction,protocol='6',is_stateless=False,description='Restricted migrated host service',tcp_options=oci.core.models.TcpOptions(destination_port_range=oci.core.models.PortRange(min=port,max=port)))
        kw.update({'source':ip,'source_type':'CIDR_BLOCK'} if direction=='INGRESS' else {'destination':ip,'destination_type':'CIDR_BLOCK'})
        net.add_network_security_group_security_rules(id,oci.core.models.AddNetworkSecurityGroupSecurityRulesDetails(security_rules=[oci.core.models.AddSecurityRuleDetails(**kw)]))
    if args.stop_originals:
        lb=oci.load_balancer.LoadBalancerClient(cfg)
        health=lb.get_backend_health('ocid1.loadbalancer.oc1.iad.aaaaaaaahzdbqrm4x6y2jlunz26wjwc5rcv6ujcyhvq342pvg4d6t4whe67a','ninjasec-standby','10.20.10.40:8080').data
        if health.status!='OK':raise RuntimeError('New portal not healthy; originals retained running')
        compute=oci.core.ComputeClient(cfg)
        for id in [OLD_UTILITY,OLD_REPLICA]:
            instance=compute.get_instance(id).data
            if instance.lifecycle_state=='RUNNING':
                compute.instance_action(id,'STOP')
                print('ORIGINAL_STOP_REQUESTED',instance.display_name,id,flush=True)

if __name__=='__main__':main()
