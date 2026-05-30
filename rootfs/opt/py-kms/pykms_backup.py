"""Backup and restore shared KMS/GUI data files."""

import io
import os
import shutil
import sqlite3
import tarfile
import time

from pykms_config import config

import pykms_auth as auth

BACKUP_FILES = (
    ('kms.db', config.DB_PATH),
    ('gui_auth.db', auth.AUTH_DB_PATH),
    ('gui_audit.db', config.AUDIT_DB),
    ('kms-policy.json', config.POLICY_FILE),
    ('.gui_secret', config.SECRET_FILE),
)


def _validate_sqlite(path):
    if not os.path.isfile(path):
        return
    with sqlite3.connect(f'file:{path}?mode=ro', uri=True) as con:
        con.execute('PRAGMA quick_check').fetchone()


def create_archive():
    buf = io.BytesIO()
    manifest = []
    with tarfile.open(fileobj=buf, mode='w:gz') as tar:
        for arcname, path in BACKUP_FILES:
            if not os.path.isfile(path):
                continue
            tar.add(path, arcname=arcname)
            manifest.append({'name': arcname, 'size': os.path.getsize(path)})
        meta = io.BytesIO(json_manifest(manifest).encode('utf-8'))
        info = tarfile.TarInfo(name='manifest.json')
        info.size = meta.getbuffer().nbytes
        tar.addfile(info, meta)
    buf.seek(0)
    return buf


def json_manifest(entries):
    import json
    return json.dumps({
        'created_at': int(time.time()),
        'files': entries,
    }, indent=2)


def restore_archive(upload_stream):
    allowed = {name for name, _ in BACKUP_FILES}
    restored = []

    with tarfile.open(fileobj=upload_stream, mode='r:gz') as tar:
        members = [m for m in tar.getmembers() if m.isfile() and m.name in allowed]
        if not members:
            raise ValueError('Archive contains no recognized backup files')

        staging = os.path.join(os.path.dirname(config.DB_PATH), f'.restore-{int(time.time())}')
        os.makedirs(staging, exist_ok=True)
        dest_map = {arc: path for arc, path in BACKUP_FILES}
        try:
            for member in members:
                tar.extract(member, path=staging)
                src = os.path.join(staging, member.name)
                if member.name.endswith('.db'):
                    _validate_sqlite(src)
                dest = dest_map[member.name]
                os.makedirs(os.path.dirname(dest) or '.', exist_ok=True)
                shutil.copy2(src, dest)
                restored.append(member.name)
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    return restored


def list_backup_files():
    rows = []
    for arcname, path in BACKUP_FILES:
        rows.append({
            'name': arcname,
            'path': path,
            'exists': os.path.isfile(path),
            'size': os.path.getsize(path) if os.path.isfile(path) else 0,
        })
    return rows
