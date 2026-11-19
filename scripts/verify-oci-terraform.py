"""Read-only production reconciliation through the existing private OCI Bastion.

The production root adopts existing resources, unlike the separate provisioning
example. No apply/destroy is performed. Plans and state must never enter Git.
"""
import base64
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile


def main():
    root = Path(__file__).resolve().parents[1]
    files = list((root / 'terraform/oci-live').glob('*.tf*'))
    files += [root / 'terraform/oci-live/.terraform.lock.hcl']
    files += list((root / 'terraform/modules/oci_infra/live').rglob('*.tf'))
    files += list((root / 'terraform/modules/oci_infra/live').rglob('*.sh'))
    files = sorted(set(files))
    digest = hashlib.sha256()
    payload = io.BytesIO()
    with tarfile.open(fileobj=payload, mode='w:gz') as archive:
        for path in files:
            relative = path.relative_to(root / 'terraform').as_posix()
            digest.update(relative.encode() + b'\0' + path.read_bytes())
            archive.add(path, arcname=relative)
    spec = importlib.util.spec_from_file_location('private_ssh', root / 'scripts/wireguard-oci-ssh.py')
    ssh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ssh)
    code = '''import base64,io,tarfile,pathlib,subprocess,os,json,hashlib
base=pathlib.Path('/opt/ninjasec-terraform/production')
base.mkdir(mode=0o700,exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(base64.b64decode(PAYLOAD)),mode='r:gz') as archive:
 for member in archive.getmembers():
  target=(base/member.name).resolve()
  if not target.is_relative_to(base.resolve()):raise RuntimeError('Unsafe archive member')
 archive.extractall(base)
tf='/opt/ninjasec-terraform/terraform'
cwd=base/'oci-live'
env=dict(os.environ,TF_CLI_CONFIG_FILE='/opt/ninjasec-terraform/terraformrc')
for args in [['fmt','-recursive',str(base)],['-chdir='+str(cwd),'init','-backend=false','-input=false','-no-color'],['-chdir='+str(cwd),'validate','-json'],['-chdir='+str(cwd),'plan','-out=production.tfplan','-input=false','-no-color','-parallelism=1']]:
 for attempt in range(3 if 'plan' in args else 1):
  r=subprocess.run([tf]+args,env=env,text=True,capture_output=True)
  if r.returncode == 0 or 'Cannot import non-existent remote object' not in r.stderr:break
 if r.returncode:raise RuntimeError(json.dumps({'step':args,'error':r.stderr[-6000:],'output':r.stdout[-1000:]}))
 if 'validate' in args and not json.loads(r.stdout)['valid']:raise RuntimeError('Validation failed')
r=subprocess.run([tf,'-chdir='+str(cwd),'show','-json','production.tfplan'],env=env,text=True,capture_output=True,check=True)
j=json.loads(r.stdout)
changes=j.get('resource_changes',[])
if not j.get('complete') or j.get('errored') or len(changes)!=63 or any(c['change']['actions']!=['no-op'] for c in changes):
 raise RuntimeError(json.dumps({'unsafe_plan':True,'actions':[(c['address'],c['change']['actions']) for c in changes]}))
print(json.dumps({'valid':True,'complete':True,'imports':sum(bool(c['change'].get('importing')) for c in changes),'resources':len(changes),'create':0,'update':0,'delete':0,'plan_sha256':hashlib.sha256((cwd/'production.tfplan').read_bytes()).hexdigest(),'files':{p.relative_to(base).as_posix():p.read_text() for p in base.rglob('*') if p.is_file() and (p.suffix in ('.tf','.sh') or p.name.endswith('.tf.json')) and '.terraform' not in p.parts}}))
'''.replace('PAYLOAD', repr(base64.b64encode(payload.getvalue()).decode()))
    result = json.loads(ssh.run('sudo -n python3 -', data=code.encode(), timeout=240))
    for relative, content in result.pop('files').items():
        (root / 'terraform' / relative).write_text(content, encoding='utf-8', newline='\n')
    result['uploaded_configuration_sha256'] = digest.hexdigest()
    print(json.dumps(result))


if __name__ == '__main__':
    main()
