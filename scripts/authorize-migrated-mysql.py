"""Replicate the portal's existing minimum SQL grants to the staged private IPs.

The admin password is supplied only in the caller's process environment and
transported through encrypted SSH stdin; never written to code or output.
"""
import importlib.util
import os
from pathlib import Path

def main():
    spec=importlib.util.spec_from_file_location('wgssh',Path(__file__).with_name('wireguard-oci-ssh.py'))
    ssh=importlib.util.module_from_spec(spec);spec.loader.exec_module(ssh)
    password=os.environ.pop('NINJASEC_MYSQL_ADMIN_PASSWORD')
    prefix='admin_password = '+repr(password)+'\n'
    code='''import sys,os,shlex,ssl
from pathlib import Path
for line in Path('/etc/systemd/system/ninjasec-portal.service').read_text().splitlines():
 if line.startswith('EnvironmentFile='):
  for row in Path(line.split('=',1)[1].lstrip('-').strip()).read_text().splitlines():
   if row and not row.startswith('#') and '=' in row:
    k,v=row.split('=',1);items=shlex.split(v);os.environ[k]=items[0] if items else ''
sys.path.insert(0,'/opt/ninjasec-portal');import app,pymysql
username,password=app.vault_credentials(os.environ['DB_SECRET_OCID'])
try:
 context=ssl.create_default_context(cafile=os.environ['DB_CA_FILE'])
 if os.environ.get('DB_PIN_CERT')=='1':
  context.check_hostname=False
  context.verify_flags |= getattr(ssl,'VERIFY_X509_PARTIAL_CHAIN',0x80000)
 db=pymysql.connect(host=os.environ['DB_HOST'],user='ninjaadmin',password=admin_password,ssl=context,autocommit=True)
 with db.cursor() as cursor:
  for host in ['10.20.10.40','10.20.10.41']:
   cursor.execute('CREATE USER IF NOT EXISTS %s@%s IDENTIFIED BY %s REQUIRE SSL',(username,host,password))
   cursor.execute('GRANT SELECT, INSERT, UPDATE, DELETE ON ninjasec.* TO %s@%s',(username,host))
   print('MINIMUM_SQL_GRANTS_AND_SSL',username,host)
 db.close()
except Exception as error:
 print('ADMIN_SQL_ERROR',type(error).__name__,error.args[0] if error.args and isinstance(error.args[0],int) else '')
 raise SystemExit(1)
'''
    print(ssh.run('sudo -n python3 -',(prefix+code).encode(),timeout=45))

if __name__=='__main__':main()
