"""Application-level admin authentication for KMS-GUI."""

import os
import sqlite3
import time

from werkzeug.security import check_password_hash, generate_password_hash

AUTH_DB_PATH = os.environ.get('GUI_AUTH_DB_PATH', '/kms/var/gui_auth.db')
MIN_PASSWORD_LEN = 12


def is_enabled():
    return os.environ.get('GUI_AUTH_ENABLED', 'false').lower() in ('1', 'true', 'yes')


def api_protection_enabled():
    """Whether /api/* requires authentication."""
    if os.environ.get('API_PUBLIC', 'false').lower() in ('1', 'true', 'yes'):
        return False
    if os.environ.get('INTERNET_MODE', 'false').lower() in ('1', 'true', 'yes'):
        return True
    if os.environ.get('NGINX_TLS_ENABLED', 'false').lower() in ('1', 'true', 'yes'):
        return True
    raw = os.environ.get('API_AUTH_REQUIRED')
    if raw is not None and str(raw).strip() != '':
        return str(raw).lower() in ('1', 'true', 'yes')
    return is_enabled()


def verify_api_bearer():
    """Validate Authorization: Bearer token against GUI_API_TOKEN."""
    import secrets
    expected = os.environ.get('GUI_API_TOKEN', '').strip()
    if not expected:
        return False
    from flask import request
    header = request.headers.get('Authorization', '')
    if not header.startswith('Bearer '):
        return False
    supplied = header[7:].strip()
    if not supplied:
        return False
    return secrets.compare_digest(supplied, expected)


def _connect():
    os.makedirs(os.path.dirname(AUTH_DB_PATH) or '.', exist_ok=True)
    con = sqlite3.connect(AUTH_DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with _connect() as con:
        con.execute(
            'CREATE TABLE IF NOT EXISTS admin_users ('
            'id INTEGER PRIMARY KEY AUTOINCREMENT, '
            'username TEXT UNIQUE NOT NULL, '
            'password_hash TEXT NOT NULL, '
            'created_at INTEGER NOT NULL, '
            'last_login INTEGER)'
        )


def is_setup_complete():
    if not is_enabled():
        return True
    init_db()
    with _connect() as con:
        row = con.execute('SELECT COUNT(*) AS c FROM admin_users').fetchone()
        return row['c'] > 0


def validate_password(password):
    if not password or len(password) < MIN_PASSWORD_LEN:
        return f'Password must be at least {MIN_PASSWORD_LEN} characters'
    return None


def create_admin(username, password):
    username = (username or '').strip()
    if not username or len(username) < 3:
        raise ValueError('Username must be at least 3 characters')
    if not username.replace('_', '').replace('-', '').isalnum():
        raise ValueError('Username: letters, numbers, _ and - only')
    err = validate_password(password)
    if err:
        raise ValueError(err)
    init_db()
    with _connect() as con:
        existing = con.execute('SELECT COUNT(*) AS c FROM admin_users').fetchone()['c']
        if existing > 0:
            raise ValueError('Setup already completed')
        now = int(time.time())
        con.execute(
            'INSERT INTO admin_users (username, password_hash, created_at) VALUES (?, ?, ?)',
            (username, generate_password_hash(password), now),
        )
        return username


def verify_login(username, password):
    init_db()
    with _connect() as con:
        row = con.execute(
            'SELECT id, username, password_hash FROM admin_users WHERE username = ?',
            ((username or '').strip(),),
        ).fetchone()
        if not row or not check_password_hash(row['password_hash'], password or ''):
            return None
        con.execute(
            'UPDATE admin_users SET last_login = ? WHERE id = ?',
            (int(time.time()), row['id']),
        )
        return {'id': row['id'], 'username': row['username']}


def get_user_by_id(user_id):
    init_db()
    with _connect() as con:
        row = con.execute(
            'SELECT id, username, created_at, last_login FROM admin_users WHERE id = ?',
            (user_id,),
        ).fetchone()
        if not row:
            return None
        return dict(row)


def change_password(user_id, current_password, new_password):
    err = validate_password(new_password)
    if err:
        raise ValueError(err)
    init_db()
    with _connect() as con:
        row = con.execute(
            'SELECT password_hash FROM admin_users WHERE id = ?',
            (user_id,),
        ).fetchone()
        if not row or not check_password_hash(row['password_hash'], current_password or ''):
            raise ValueError('Current password is incorrect')
        con.execute(
            'UPDATE admin_users SET password_hash = ? WHERE id = ?',
            (generate_password_hash(new_password), user_id),
        )


def get_admin_profile():
    init_db()
    with _connect() as con:
        row = con.execute(
            'SELECT id, username, created_at, last_login FROM admin_users ORDER BY id LIMIT 1'
        ).fetchone()
        return dict(row) if row else None
