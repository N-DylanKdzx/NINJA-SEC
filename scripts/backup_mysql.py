#!/usr/bin/env python3
"""Create and validate a compressed backup of the private OCI MySQL database."""

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from uuid import uuid4


def mysql_option(value):
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r') + '"'


def backup(args):
    sys.path.insert(0, args.portal_dir)
    from vault_credentials import read_mysql_credentials

    username, password = read_mysql_credentials(args.secret_ocid)
    output = Path(args.output)
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    destination = output / f'ninjasec-{stamp}-{uuid4().hex[:8]}.sql.gz'
    with tempfile.TemporaryDirectory(dir=output) as directory:
        temporary = Path(directory)
        options = temporary / 'client.cnf'
        options.write_text('[client]\n' + ''.join(
            f'{key}={mysql_option(value)}\n' for key, value in {
                'host': args.host, 'user': username, 'password': password,
                'ssl-mode': 'VERIFY_CA', 'ssl-ca': args.ca_file,
            }.items()), encoding='utf-8')
        archive = temporary / 'dump.sql.gz'
        command = [args.mysqldump, f'--defaults-file={options}', '--single-transaction',
                   '--quick', '--no-tablespaces', '--set-gtid-purged=OFF',
                   '--skip-lock-tables', '--', args.database]
        if os.environ.get('DB_PIN_CERT') == '1':
            # MySQL's CLI lacks PARTIAL_CHAIN, used by the portal's pinned-leaf
            # trust. Authenticate a fresh TLS1.2 session with OpenSSL, then force
            # the official client to reuse it. Never permit an unverified retry.
            session = temporary / 'verified-session.pem'
            result = subprocess.run(['openssl', 's_client', '-starttls', 'mysql',
                '-connect', args.host + ':3306', '-CAfile', args.ca_file,
                '-partial_chain', '-verify_return_error', '-tls1_2',
                '-sess_out', str(session), '-quiet', '-no_ign_eof'],
                input=b'', stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=20)
            if result.returncode or not session.exists() or not session.stat().st_size:
                raise RuntimeError('Pinned certificate TLS session verification failed')
            command[2:2] = ['--tls-version=TLSv1.2', f'--ssl-session-data={session}',
                            '--ssl-session-data-continue-on-failed-reuse=OFF']
        with subprocess.Popen(command, stdout=subprocess.PIPE) as process:
            try:
                with gzip.open(archive, 'wb') as compressed:
                    shutil.copyfileobj(process.stdout, compressed)
            except BaseException:
                process.kill()
                raise
            if process.wait():
                raise RuntimeError('mysqldump failed')
        with gzip.open(archive, 'rb') as compressed:
            if not compressed.read(1):
                raise RuntimeError('mysqldump emitted no data')
            while compressed.read(1024 * 1024):
                pass
        with archive.open('rb') as source:
            digest = hashlib.sha256()
            for chunk in iter(lambda: source.read(1024 * 1024), b''):
                digest.update(chunk)
        archive.rename(destination)
    print(f'BACKUP_OK {destination} bytes={destination.stat().st_size} sha256={digest.hexdigest()}')
    return {'path': str(destination), 'bytes': destination.stat().st_size,
            'sha256': digest.hexdigest(), 'createdAt': datetime.now(timezone.utc).isoformat()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('host', 'secret-ocid', 'ca-file', 'portal-dir', 'output'):
        parser.add_argument(f'--{name}', required=True)
    parser.add_argument('--database', default='ninjasec')
    parser.add_argument('--mysqldump', default='/usr/bin/mysqldump')
    os.umask(0o077)
    backup(parser.parse_args())
