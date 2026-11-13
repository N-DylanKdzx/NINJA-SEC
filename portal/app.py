import base64
import hmac
import json
import os
import re
import secrets
import ssl
import time
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from wsgiref.simple_server import make_server

import pymysql


ROOT = Path(__file__).resolve().parent
STATUSES = {'abierto', 'en_progreso', 'resuelto'}
FIELDS = 'id, title, description, status, created_at, updated_at'
SESSION_SECONDS = 3600
SESSION_COOKIE = '__Host-ninjasec-session'
SESSIONS = {}


@lru_cache(maxsize=1)
def vault_credentials(secret_ocid):
    from oci.exceptions import RequestException, ServiceError
    from vault_credentials import read_mysql_credentials

    try:
        return read_mysql_credentials(secret_ocid)
    except (RequestException, ServiceError, ValueError, OSError) as error:
        raise RuntimeError('No se pudo obtener la credencial de Vault.') from error


def connect():
    secret_ocid = os.environ.get('DB_SECRET_OCID')
    if secret_ocid:
        user, password = vault_credentials(secret_ocid)
    else:
        user, password = os.environ['DB_USER'], os.environ['DB_PASSWORD']
    context = ssl.create_default_context(cafile=os.environ['DB_CA_FILE'])
    if os.environ.get('DB_PIN_CERT') == '1':
        context.check_hostname = False
        context.verify_flags |= getattr(ssl, 'VERIFY_X509_PARTIAL_CHAIN', 0x80000)
    return pymysql.connect(
        host=os.environ['DB_HOST'], user=user,
        password=password, database=os.environ.get('DB_NAME', 'ninjasec'),
        ssl=context, autocommit=True, connect_timeout=4, read_timeout=5, write_timeout=5,
        cursorclass=pymysql.cursors.DictCursor,
    )


def json_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def respond(start, status, data=None, *, content_type='application/json; charset=utf-8', headers=()):
    if isinstance(data, bytes):
        body = data
    elif data is None:
        body = b''
    else:
        body = json.dumps(data, ensure_ascii=False, default=json_value).encode()
    start(status, [
        ('Content-Type', content_type), ('Content-Length', str(len(body))),
        ('Cache-Control', 'no-store'), ('X-Content-Type-Options', 'nosniff'),
        ('Content-Security-Policy', "default-src 'self'; frame-ancestors 'none'; base-uri 'none'"),
        *headers,
    ])
    return [body]


def authorized(environ):
    scheme, _, encoded = environ.get('HTTP_AUTHORIZATION', '').partition(' ')
    if scheme.lower() != 'basic':
        return False
    try:
        supplied = base64.b64decode(encoded, validate=True)
    except ValueError:
        return False
    expected = (os.environ['PORTAL_USER'] + ':' + os.environ['PORTAL_PASSWORD']).encode()
    return hmac.compare_digest(supplied, expected)


def session_token(environ):
    for cookie in environ.get('HTTP_COOKIE', '').split(';'):
        name, _, value = cookie.strip().partition('=')
        if name != SESSION_COOKIE:
            continue
        return value if re.fullmatch(r'[0-9a-f]{64}', value) else None
    return None


def session_header(value, max_age):
    return ('Set-Cookie', f'{SESSION_COOKIE}={value}; Path=/; Max-Age={max_age}; Secure; HttpOnly; SameSite=Strict')


def session_endpoint(environ, start, path, method):
    if method != 'POST':
        return respond(start, '405 Method Not Allowed', headers=(('Allow', 'POST'),))
    if environ.get('HTTP_X_NINJASEC_ACTION') != '1':
        return respond(start, '403 Forbidden', {'error': 'Solicitud de acceso no permitida.'})
    if path == '/auth/logout':
        SESSIONS.pop(session_token(environ), None)
        return respond(start, '204 No Content', headers=(session_header('', 0),))
    try:
        if environ.get('CONTENT_TYPE', '').split(';')[0].strip() != 'application/json':
            raise ValueError
        size = int(environ.get('CONTENT_LENGTH') or '0')
        if not 0 < size <= 8192:
            raise ValueError
        data = json.loads(environ['wsgi.input'].read(size))
        username, password = data.get('username'), data.get('password')
        if not isinstance(username, str) or not isinstance(password, str):
            raise ValueError
        user_ok = hmac.compare_digest(username.encode(), os.environ['PORTAL_USER'].encode())
        password_ok = hmac.compare_digest(password.encode(), os.environ['PORTAL_PASSWORD'].encode())
    except (ValueError, AttributeError):
        return respond(start, '400 Bad Request', {'error': 'Completa los datos de acceso.'})
    if not (user_ok and password_ok):
        return respond(start, '401 Unauthorized', {'error': 'Usuario o contraseña incorrectos.'})
    now = time.monotonic()
    for token, expiry in list(SESSIONS.items()):
        if expiry <= now:
            SESSIONS.pop(token, None)
    SESSIONS.pop(session_token(environ), None)
    token = secrets.token_hex(32)
    SESSIONS[token] = now + SESSION_SECONDS
    return respond(start, '204 No Content', headers=(session_header(token, SESSION_SECONDS),))


def incident_data(environ):
    if environ.get('CONTENT_TYPE', '').split(';')[0].strip() != 'application/json':
        raise ValueError('Se requiere application/json.')
    size = int(environ.get('CONTENT_LENGTH') or '0')
    if not 0 < size <= 16384:
        raise ValueError('El cuerpo debe tener entre 1 y 16384 bytes.')
    data = json.loads(environ['wsgi.input'].read(size))
    if not isinstance(data, dict):
        raise ValueError('Se esperaba un objeto JSON.')
    title, description, status = (data.get(k) for k in ('title', 'description', 'status'))
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 160:
        raise ValueError('El título debe tener entre 1 y 160 caracteres.')
    if not isinstance(description, str) or len(description) > 8000:
        raise ValueError('La descripción admite hasta 8000 caracteres.')
    if not isinstance(status, str) or status not in STATUSES:
        raise ValueError('El estado del incidente no es válido.')
    return title.strip(), description, status


def application(environ, start):
    method, path = environ['REQUEST_METHOD'], environ['PATH_INFO']
    if path == '/health' and method == 'GET':
        try:
            with connect() as db, db.cursor() as cur:
                cur.execute('SELECT id FROM incidents LIMIT 1')
            return respond(start, '200 OK', {'status': 'ok'})
        except (pymysql.MySQLError, OSError, ValueError, RuntimeError):
            return respond(start, '503 Service Unavailable', {'status': 'unavailable'})

    if path in ('/auth/login', '/auth/logout'):
        return session_endpoint(environ, start, path, method)
    # Keep explicit Basic auth for scripts; browser requests use the session.
    signed_in = (SESSIONS.get(session_token(environ), 0) > time.monotonic()
                 or ('HTTP_SEC_FETCH_SITE' not in environ and authorized(environ)))
    assets = {
        '/': ('index.html' if signed_in else 'login.html', 'text/html'),
        '/portal.css': ('portal.css', 'text/css'),
        '/login.js': ('login.js', 'text/javascript'),
    }
    if signed_in:
        assets['/portal.js'] = ('portal.js', 'text/javascript')
    if path in assets and method == 'GET':
        filename, mime = assets[path]
        return respond(start, '200 OK', (ROOT / filename).read_bytes(), content_type=mime + '; charset=utf-8')

    if not signed_in:
        return respond(start, '401 Unauthorized', {'error': 'Autenticación requerida.'})

    item = re.fullmatch(r'/api/incidents/([1-9][0-9]{0,18})', path)
    collection = path == '/api/incidents'
    if not collection and not item:
        return respond(start, '404 Not Found', {'error': 'Ruta no encontrada.'})
    allowed = ('GET', 'POST') if collection else ('GET', 'PUT', 'DELETE')
    if method not in allowed:
        return respond(start, '405 Method Not Allowed', headers=(('Allow', ', '.join(allowed)),))
    if method != 'GET' and environ.get('HTTP_X_NINJASEC_ACTION') != '1':
        return respond(start, '403 Forbidden', {'error': 'Falta la cabecera de protección de escritura.'})

    try:
        values = incident_data(environ) if method in ('POST', 'PUT') else None
        with connect() as db, db.cursor() as cur:
            if collection and method == 'GET':
                cur.execute(f'SELECT {FIELDS} FROM incidents ORDER BY id DESC LIMIT 200')
                return respond(start, '200 OK', cur.fetchall())
            if collection:
                cur.execute('INSERT INTO incidents (title, description, status) VALUES (%s, %s, %s)', values)
                return respond(start, '201 Created', {'id': cur.lastrowid},
                               headers=(('Location', f'/api/incidents/{cur.lastrowid}'),))
            incident_id = int(item[1])
            if method == 'DELETE':
                cur.execute('DELETE FROM incidents WHERE id=%s', (incident_id,))
                if cur.rowcount:
                    return respond(start, '204 No Content')
            else:
                if method == 'PUT':
                    cur.execute('UPDATE incidents SET title=%s, description=%s, status=%s WHERE id=%s',
                                (*values, incident_id))
                cur.execute(f'SELECT {FIELDS} FROM incidents WHERE id=%s', (incident_id,))
                row = cur.fetchone()
                if row:
                    return respond(start, '200 OK', row)
        return respond(start, '404 Not Found', {'error': 'Incidente no encontrado.'})
    except (ValueError, UnicodeError) as error:
        return respond(start, '400 Bad Request', {'error': str(error)})
    except (pymysql.MySQLError, OSError, RuntimeError):
        return respond(start, '503 Service Unavailable', {'error': 'Base de datos no disponible.'})


if __name__ == '__main__':
    required = ('PORTAL_USER', 'PORTAL_PASSWORD', 'DB_HOST', 'DB_CA_FILE')
    if not os.environ.get('DB_SECRET_OCID'):
        required += ('DB_USER', 'DB_PASSWORD')
    for variable in required:
        if not os.environ.get(variable):
            raise SystemExit(f'Falta la variable {variable}')
    with make_server(os.environ.get('PORTAL_BIND', '127.0.0.1'), 8080, application) as server:
        server.serve_forever()
