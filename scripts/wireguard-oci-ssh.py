"""Run a supplied command through the existing short-lived OCI Bastion session."""
import importlib.util
import json
from pathlib import Path
import subprocess

def run(command, data=None, timeout=60):
    spec=importlib.util.spec_from_file_location('wg_probe',Path(__file__).with_name('probe-wireguard.py'))
    probe=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    session=json.loads(Path('E:/NINJA-SEC/Credenciales de Acceso/oci-wireguard-utility-session.json').read_text())
    args=probe.ssh_command(session['sessionId'],command)
    args[-2]='opc@'+session['privateIp']
    result=subprocess.run(args,input=data,capture_output=True,timeout=timeout)
    output=result.stdout.decode('utf-8',errors='replace')
    error=result.stderr.decode('utf-8',errors='replace')
    if result.returncode:
        raise RuntimeError(json.dumps({'code':result.returncode,'stdout':output,'stderr':error}))
    return output
