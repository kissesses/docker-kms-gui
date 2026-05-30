"""Audit log for admin actions."""

import os
import sqlite3
import time

from pykms_config import config


def _connect():
    os.makedirs(os.path.dirname(config.AUDIT_DB) or '.', exist_ok=True)
    con = sqlite3.connect(config.AUDIT_DB)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with _connect() as con:
        con.execute(
            'CREATE TABLE IF NOT EXISTS audit_log ('
            'id INTEGER PRIMARY KEY AUTOINCREMENT, '
            'created_at INTEGER NOT NULL, '
            'username TEXT, '
            'action TEXT NOT NULL, '
            'detail TEXT, '
            'ip TEXT)'
        )


def log(action, detail='', username=None, ip=None):
    init_db()
    from flask import request, session
    if username is None:
        username = session.get('username')
    if ip is None and request:
        ip = request.headers.get('X-Real-IP') or request.remote_addr
    with _connect() as con:
        con.execute(
            'INSERT INTO audit_log (created_at, username, action, detail, ip) VALUES (?, ?, ?, ?, ?)',
            (int(time.time()), username, action, detail, ip),
        )


def recent(limit=50):
    init_db()
    with _connect() as con:
        rows = con.execute(
            'SELECT * FROM audit_log ORDER BY id DESC LIMIT ?',
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]
