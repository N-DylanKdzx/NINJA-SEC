"""Exercise the real LB alarm using an unhealthy backup, retaining the healthy primary.

No alarm threshold, application service or firewall rule is changed. Cleanup runs
in finally; a subsequent run refuses to overwrite an existing test backend.
"""
import datetime as dt
import json
import time
import oci

LB = 'ocid1.loadbalancer.oc1.iad.aaaaaaaahzdbqrm4x6y2jlunz26wjwc5rcv6ujcyhvq342pvg4d6t4whe67a'
BACKEND_SET = 'ninjasec-standby'
TEST = '10.20.10.254:65534'
ALARM = 'ocid1.alarm.oc1.iad.amaaaaaa3nxgmgaarzael5eqkvcwaajwaolff3b4fxs2nxddcuv7xgyzlc2q'


def main():
    cfg = oci.config.from_file(profile_name='NINJA_SEC_TERRAFORM')
    lb = oci.load_balancer.LoadBalancerClient(cfg)
    monitoring = oci.monitoring.MonitoringClient(cfg)
    start = dt.datetime.now(dt.timezone.utc)

    def status():
        return monitoring.list_alarms_status(cfg['tenancy'], display_name='ninjasec-portal-backend-unhealthy').data[0].status

    def primary_health():
        return lb.get_backend_health(LB, BACKEND_SET, '10.20.10.40:8080').data.status

    if primary_health() != 'OK' or status() != 'OK':
        raise RuntimeError('Primary backend and alarm must be OK before testing')
    network = oci.core.VirtualNetworkClient(cfg)
    assigned = oci.pagination.list_call_get_all_results(network.list_private_ips, subnet_id='ocid1.subnet.oc1.iad.aaaaaaaazpxp43ofolxis2j6cawsqajxpzqtezchvqpbqjii25ojl3lwv4rq').data
    if any(ip.ip_address == '10.20.10.254' for ip in assigned):
        raise RuntimeError('The synthetic test IP is assigned; refusing test')
    backends = lb.get_backend_set(LB, BACKEND_SET).data.backends
    if any(b.name == TEST for b in backends):
        raise RuntimeError('Test backend already exists; inspect and clean up explicitly')
    created = False
    try:
        lb.create_backend(load_balancer_id=LB, backend_set_name=BACKEND_SET, create_backend_details=oci.load_balancer.models.CreateBackendDetails(ip_address='10.20.10.254', port=65534, weight=1, backup=True, offline=False, drain=False))
        created = True
        print(json.dumps({'test_started': start.isoformat(), 'test_backend': TEST, 'backup': True}), flush=True)
        for _ in range(36):
            time.sleep(20)
            health = primary_health()
            alarm = status()
            print(json.dumps({'time': dt.datetime.now(dt.timezone.utc).isoformat(), 'primary': health, 'alarm': alarm}), flush=True)
            if health != 'OK':
                raise RuntimeError('Primary backend health changed; aborting test')
            if alarm == 'FIRING':
                print('FIRING_CONFIRMED', flush=True)
                break
        else:
            raise RuntimeError('Alarm did not fire within the bounded test window')
    finally:
        if created:
            lb.delete_backend(LB, BACKEND_SET, TEST)
            for _ in range(30):
                time.sleep(2)
                if all(b.name != TEST for b in lb.get_backend_set(LB, BACKEND_SET).data.backends):
                    break
            else:
                raise RuntimeError('Test backend cleanup did not complete')
            print('TEST_BACKEND_REMOVED', flush=True)
    for _ in range(30):
        time.sleep(20)
        alarm = status()
        print(json.dumps({'recovery_time': dt.datetime.now(dt.timezone.utc).isoformat(), 'alarm': alarm, 'primary': primary_health()}), flush=True)
        if alarm == 'OK':
            history = monitoring.get_alarm_history(ALARM, alarm_historytype='STATE_TRANSITION_HISTORY', timestamp_greater_than_or_equal_to=start).data
            print(json.dumps({'recovered': True, 'history': oci.util.to_dict(history)}, default=str), flush=True)
            return
    raise RuntimeError('Backend removed but alarm recovery is not yet verified')


if __name__ == '__main__':
    main()
