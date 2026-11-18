"""Run a supplied command through the existing short-lived OCI Bastion session."""
import importlib.util
import json
from pathlib import Path
import subprocess
import datetime as dt
import time
import oci

def run(command, data=None, timeout=60, host='10.20.10.40'):
    spec=importlib.util.spec_from_file_location('wg_probe',Path(__file__).with_name('probe-wireguard.py'))
    probe=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    root=Path('E:/NINJA-SEC/Credenciales de Acceso')
    path=root / ('oci-wireguard-utility-session.json' if host=='10.20.10.36' else 'oci-'+host.replace('.','-')+'-session.json')
    session=json.loads(path.read_text()) if path.exists() else None
    client=oci.bastion.BastionClient(oci.config.from_file(profile_name='NINJA_SEC_TERRAFORM'))
    active=None
    if session:
        try:active=client.get_session(session['sessionId']).data
        except oci.exceptions.ServiceError as exc:
            if exc.status!=404:raise
    if not active or active.lifecycle_state!='ACTIVE' or active.time_created+dt.timedelta(seconds=active.session_ttl_in_seconds)<dt.datetime.now(dt.timezone.utc)+dt.timedelta(seconds=60):
        public=subprocess.check_output(['ssh-keygen','-y','-f','C:/Users/DYLAN/.ssh/ninjasec_oci_bastion_rsa'],text=True).strip()
        active=client.create_session(oci.bastion.models.CreateSessionDetails(bastion_id=probe.BASTION,target_resource_details=oci.bastion.models.CreatePortForwardingSessionTargetResourceDetails(target_resource_private_ip_address=host,target_resource_port=22),key_details=oci.bastion.models.PublicKeyDetails(public_key_content=public),display_name='ninjasec-private-admin',session_ttl_in_seconds=1800)).data
        for _ in range(30):
            active=client.get_session(active.id).data
            if active.lifecycle_state=='ACTIVE':break
            if active.lifecycle_state in ('FAILED','DELETED'):raise RuntimeError('Bastion session failed')
            time.sleep(2)
        else:raise RuntimeError('Bastion session did not activate')
        session={'sessionId':active.id,'privateIp':host}
        path.write_text(json.dumps(session),encoding='utf-8')
        time.sleep(8) # ACTIVE precedes SSH authorization propagation.
    args=probe.ssh_command(session['sessionId'],command)
    args[-2]='opc@'+session['privateIp']
    result=subprocess.run(args,input=data,capture_output=True,timeout=timeout)
    output=result.stdout.decode('utf-8',errors='replace')
    error=result.stderr.decode('utf-8',errors='replace')
    if result.returncode:
        raise RuntimeError(json.dumps({'code':result.returncode,'stdout':output,'stderr':error}))
    return output
