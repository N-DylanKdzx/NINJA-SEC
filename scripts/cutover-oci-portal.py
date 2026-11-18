"""Switch the existing LB only after the staged portal passes its health check."""
import time
import oci

LB='ocid1.loadbalancer.oc1.iad.aaaaaaaahzdbqrm4x6y2jlunz26wjwc5rcv6ujcyhvq342pvg4d6t4whe67a'
SET='ninjasec-standby'

def main():
    cfg=oci.config.from_file(profile_name='NINJA_SEC_TERRAFORM')
    client=oci.load_balancer.LoadBalancerClient(cfg)
    net=oci.core.VirtualNetworkClient(cfg)
    group='ocid1.networksecuritygroup.oc1.iad.aaaaaaaanasaxkrlu4szysqwp37sz4hwj5hac2gvo27awryyxyfaaf4x5ipa'
    rules=net.list_network_security_group_security_rules(group).data
    if not any(r.direction=='EGRESS' and r.destination=='10.20.10.40/32' and r.tcp_options and r.tcp_options.destination_port_range.min==8080 for r in rules):
        net.add_network_security_group_security_rules(group,oci.core.models.AddNetworkSecurityGroupSecurityRulesDetails(security_rules=[oci.core.models.AddSecurityRuleDetails(direction='EGRESS',protocol='6',destination='10.20.10.40/32',destination_type='CIDR_BLOCK',is_stateless=False,description='LB to migrated portal only',tcp_options=oci.core.models.TcpOptions(destination_port_range=oci.core.models.PortRange(min=8080,max=8080)))]))
    def wait(response):
        id=response.headers.get('opc-work-request-id')
        if not id:return
        for _ in range(40):
            job=client.get_work_request(id).data
            if job.lifecycle_state=='SUCCEEDED':return
            if job.lifecycle_state=='FAILED':raise RuntimeError('LB update failed: '+id)
            time.sleep(2)
        raise RuntimeError('LB update pending: '+id)
    current=client.get_backend_set(LB,SET).data
    if not any(b.ip_address=='10.20.10.40' for b in current.backends):
        wait(client.create_backend(oci.load_balancer.models.CreateBackendDetails(ip_address='10.20.10.40',port=8080,weight=1,backup=False,drain=False,offline=False),LB,SET))
    for _ in range(40):
        health=client.get_backend_health(LB,SET,'10.20.10.40:8080').data
        if health.status=='OK':break
        time.sleep(3)
    else:raise RuntimeError('New backend not healthy; original retained')
    print('NEW_BACKEND_HEALTH',health.status,flush=True)
    current=client.get_backend_set(LB,SET).data
    if any(b.ip_address=='10.20.10.36' for b in current.backends):
        wait(client.update_backend(update_backend_details=oci.load_balancer.models.UpdateBackendDetails(weight=1,backup=False,drain=True,offline=False),load_balancer_id=LB,backend_set_name=SET,backend_name='10.20.10.36:8080'))
        time.sleep(5)
        wait(client.delete_backend(LB,SET,'10.20.10.36:8080'))
    print('PORTAL_CUTOVER',[(b.ip_address,b.port) for b in client.get_backend_set(LB,SET).data.backends],flush=True)

if __name__=='__main__':main()
