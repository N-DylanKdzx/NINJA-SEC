"""Restore the cron-produced archive to an isolated schema and remove it.

Admin secret enters via process environment; it never enters source or output.
The OCI bytes have the same SHA256 as Azure's authenticated read-back.
"""
import base64
import hashlib
import importlib.util
import os
from pathlib import Path
import oci

OBJECT='mysql/ninjasec-20261118T235002Z-316e027f.sql.gz'
SHA='b4c72c05ddcefbd9b8336e8aa61150237f27f8434ec3025a5ccb0e117c66f97b'

def main():
    client=oci.object_storage.ObjectStorageClient(oci.config.from_file(profile_name='NINJA_SEC_TERRAFORM'))
    archive=client.get_object('idyjnbepyaq2','ninjasec-backup-staging',OBJECT).data.content
    if hashlib.sha256(archive).hexdigest()!=SHA:raise RuntimeError('Backup hash mismatch')
    password=os.environ.pop('NINJASEC_MYSQL_ADMIN_PASSWORD')
    prefix='admin_password='+repr(password)+'\narchive64='+repr(base64.b64encode(archive).decode())+'\n'
    code='''import os,sys,shlex,ssl,base64,gzip,re,uuid
from pathlib import Path
for row in Path('/etc/ninjasec-portal.env').read_text().splitlines():
 if row and not row.startswith('#') and '=' in row:
  k,v=row.split('=',1);values=shlex.split(v);os.environ[k]=values[0] if values else ''
sys.path.insert(0,'/opt/ninjasec-portal');import pymysql
sql=gzip.decompress(base64.b64decode(archive64)).decode('utf-8')
if re.search(r'(?im)^\\s*(?:CREATE|DROP)\\s+DATABASE|^\\s*USE\\s',sql):raise RuntimeError('Dump selects an external schema')
ctx=ssl.create_default_context(cafile=os.environ['DB_CA_FILE']);ctx.check_hostname=False;ctx.verify_flags|=getattr(ssl,'VERIFY_X509_PARTIAL_CHAIN',0x80000)
schema='ninjasec_verify_'+uuid.uuid4().hex[:12]
db=pymysql.connect(host=os.environ['DB_HOST'],user='ninjaadmin',password=admin_password,ssl=ctx,autocommit=True,client_flag=pymysql.constants.CLIENT.MULTI_STATEMENTS,cursorclass=pymysql.cursors.DictCursor)
try:
 with db.cursor() as c:
  c.execute('CREATE DATABASE `'+schema+'`');db.select_db(schema)
  c.execute(sql)
  while c.nextset():pass
  c.execute('SELECT COUNT(*) AS row_count FROM incidents');rows=c.fetchone()['row_count']
  c.execute('SELECT COUNT(*) AS matches FROM incidents WHERE title=%s',('NINJASEC_BACKUP_CANARY_35ae80d88346',));matches=c.fetchone()['matches']
  if matches!=1:raise RuntimeError('Restored canary missing')
  c.execute("SELECT COUNT(*) AS cols FROM information_schema.columns WHERE table_schema=%s AND table_name='incidents'",(schema,));columns=c.fetchone()['cols']
  c.execute("SHOW SESSION STATUS LIKE 'Ssl_cipher'");cipher=c.fetchone()['Value']
  c.execute('SELECT COUNT(*) AS remaining FROM ninjasec.incidents WHERE title=%s',('NINJASEC_BACKUP_CANARY_35ae80d88346',));remaining=c.fetchone()['remaining']
  if remaining:raise RuntimeError('Synthetic source row was not cleaned')
  print('RESTORE_ISOLATED_OK schema='+schema+' rows='+str(rows)+' canary='+str(matches)+' columns='+str(columns)+' tls='+cipher+' sourceCanaryRemaining='+str(remaining))
finally:
 with db.cursor() as c:c.execute('DROP DATABASE IF EXISTS `'+schema+'`')
 db.close();print('RESTORE_SCHEMA_CLEANED')
'''
    spec=importlib.util.spec_from_file_location('wgssh',Path(__file__).with_name('wireguard-oci-ssh.py'));ssh=importlib.util.module_from_spec(spec);spec.loader.exec_module(ssh)
    print('BACKUP_SHA256',SHA)
    print(ssh.run('sudo -n python3 -',(prefix+code).encode(),timeout=60))

if __name__=='__main__':main()
