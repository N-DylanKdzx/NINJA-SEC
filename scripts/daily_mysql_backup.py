#!/usr/bin/env python3
"""Daily TLS MySQL dump, verified OCI archive and fresh manifest for Azure MI."""
import argparse
import base64
import fcntl
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

from backup_mysql import backup

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);args=parser.parse_args()
    cfg=json.loads(Path(args.config).read_text());os.umask(0o077)
    sys.path.insert(0,cfg['portal_dir']);sys.path.insert(0,cfg['oci_sdk_dir'])
    import oci
    Path('/run/ninjasec-backup').mkdir(mode=0o700,exist_ok=True)
    lock=open('/run/ninjasec-backup/backup.lock','w')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    signer=oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    cloud={'region':signer.region};objects=oci.object_storage.ObjectStorageClient(cloud,signer=signer,timeout=(10,60))
    try:
        result=backup(SimpleNamespace(host=os.environ['DB_HOST'],secret_ocid=os.environ['DB_SECRET_OCID'],
            ca_file=os.environ['DB_CA_FILE'],portal_dir=cfg['portal_dir'],output=cfg['output'],
            database=os.environ.get('DB_NAME','ninjasec'),mysqldump=cfg['mysqldump']))
        path=Path(result['path']);name='mysql/'+path.name
        if result['bytes']>100*1024*1024:raise RuntimeError('Backup exceeds verified 100MiB copy limit')
        with path.open('rb') as data:
            objects.put_object(cfg['namespace'],cfg['bucket'],name,data,content_type='application/gzip',
                content_md5=base64.b64encode(__import__('hashlib').md5(path.read_bytes()).digest()).decode(),
                opc_meta={'sha256':result['sha256']},if_none_match='*')
        archive=objects.get_object(cfg['namespace'],cfg['bucket'],name).data.content
        if __import__('hashlib').sha256(archive).hexdigest()!=result['sha256']:raise RuntimeError('OCI read-back SHA mismatch')
        manifest=dict(schemaVersion=1,objectName=name,bytes=result['bytes'],sha256=result['sha256'],createdAt=result['createdAt'])
        objects.put_object(cfg['namespace'],cfg['bucket'],'mysql/latest.json',json.dumps(manifest).encode(),content_type='application/json')
        Path(cfg['output'],'last-success.json').write_text(json.dumps(manifest),encoding='utf-8')
        print('DAILY_MYSQL_BACKUP_OK '+json.dumps(manifest),flush=True)
    except Exception as exc:
        print('DAILY_MYSQL_BACKUP_FAILED '+type(exc).__name__,file=sys.stderr,flush=True)
        try:
            oci.ons.NotificationDataPlaneClient(cloud,signer=signer,
                service_endpoint=cfg.get('notification_endpoint','https://cell1.notification.us-ashburn-1.oci.oraclecloud.com')).publish_message(cfg['topic_id'],
                oci.ons.models.MessageDetails(title='NINJA-SEC: prueba controlada de alerta de respaldo' if cfg.get('alert_test') else 'NINJA-SEC: fallo del respaldo MySQL',
                    body=('Prueba controlada, sin afectar el respaldo diario. ' if cfg.get('alert_test') else '')+
                        'El respaldo fallo en '+os.uname().nodename+'. Tipo: '+type(exc).__name__+'. Revisar ninjasec-mysql-backup.service. No se publico un manifiesto nuevo.'))
            print('BACKUP_FAILURE_NOTIFICATION_PUBLISHED',flush=True)
        except Exception as notification:
            print('BACKUP_FAILURE_NOTIFICATION_FAILED '+type(notification).__name__+
                ' status='+str(getattr(notification,'status',None))+' code='+str(getattr(notification,'code',None)),file=sys.stderr,flush=True)
        raise SystemExit(1)
    finally:lock.close()

if __name__=='__main__':main()
