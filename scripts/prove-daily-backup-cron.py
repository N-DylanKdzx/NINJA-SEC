"""Run on the utility host: prove crond triggers the real backup, with test data.

The unique test incident and one-time proof crontab are removed in finally.
"""
import datetime as dt
import json
import os
from pathlib import Path
import shlex
import sys
import time
import uuid

def main():
    for row in Path('/etc/ninjasec-portal.env').read_text().splitlines():
        if row and not row.startswith('#') and '=' in row:
            key,value=row.split('=',1);items=shlex.split(value);os.environ[key]=items[0] if items else ''
    sys.path[:0]=['/opt/ninjasec-portal','/opt/ninjasec-portal/oci-deps']
    import app
    title='NINJASEC_BACKUP_CANARY_'+uuid.uuid4().hex[:12]
    proof=Path('/etc/cron.d/ninjasec-mysql-backup-proof')
    incident=None
    try:
        with app.connect() as db,db.cursor() as cursor:
            cursor.execute("SHOW COLUMNS FROM incidents LIKE 'status'")
            column=cursor.fetchone()
            status=column.get('Default') or column['Type'].split("'")[1]
            cursor.execute('INSERT INTO incidents (title,description,status) VALUES (%s,%s,%s)',
                (title,'Prueba controlada de respaldo; sin datos reales. Se elimina al finalizar.',status))
            incident=cursor.lastrowid
        start=dt.datetime.now(dt.timezone.utc)
        schedule=(start+dt.timedelta(minutes=2)).replace(second=0,microsecond=0)
        proof.write_text('CRON_TZ=UTC\n'+schedule.strftime('%M %H %d %m')+' * root /usr/bin/systemctl start ninjasec-mysql-backup.service\n')
        proof.chmod(0o644)
        print('CRON_PROOF_SCHEDULED',schedule.isoformat(),'CANARY',title,flush=True)
        deadline=time.monotonic()+190
        while time.monotonic()<deadline:
            file=Path('/var/lib/ninjasec-backup/last-success.json')
            if file.exists():
                manifest=json.loads(file.read_text())
                if dt.datetime.fromisoformat(manifest['createdAt'])>start:
                    import gzip
                    local=Path('/var/lib/ninjasec-backup')/manifest['objectName'].split('/')[-1]
                    if title not in gzip.decompress(local.read_bytes()).decode():raise RuntimeError('Backup does not contain test data')
                    print('CRON_DATA_BACKUP_VERIFIED',json.dumps(manifest),'CANARY',title,flush=True)
                    return
            time.sleep(3)
        raise RuntimeError('Cron did not produce a verified backup within the test window')
    finally:
        proof.unlink(missing_ok=True)
        if incident is not None:
            with app.connect() as db,db.cursor() as cursor:
                cursor.execute('DELETE FROM incidents WHERE id=%s AND title=%s',(incident,title))
            print('CANARY_AND_PROOF_CRON_CLEANED',flush=True)

if __name__=='__main__':main()
