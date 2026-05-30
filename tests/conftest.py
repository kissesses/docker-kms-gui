import os
import sqlite3
import subprocess
import sys

import pytest

ROOT = os.path.join(os.path.dirname(__file__), '..', 'rootfs', 'opt', 'py-kms')
sys.path.insert(0, ROOT)

PYKMS_COMMIT = 'b0e1615dec06'
PYKMS_REPO = 'https://github.com/Py-KMS-Organization/py-kms.git'


@pytest.fixture(scope='session')
def pykms_src(tmp_path_factory):
    dest = tmp_path_factory.mktemp('py-kms-src')
    subprocess.run(
        ['git', 'clone', '--filter=blob:none', PYKMS_REPO, str(dest)],
        check=True,
        capture_output=True,
    )
    subprocess.run(['git', 'checkout', PYKMS_COMMIT], cwd=dest, check=True, capture_output=True)
    pykms_dir = dest / 'py-kms'
    if str(pykms_dir) not in sys.path:
        sys.path.insert(0, str(pykms_dir))
    return pykms_dir


def _purge_pykms_modules():
    for name in list(sys.modules):
        if name.startswith('pykms_'):
            del sys.modules[name]


@pytest.fixture()
def auth_db(tmp_path, monkeypatch):
    import pykms_auth as auth
    import werkzeug.security

    path = str(tmp_path / 'gui_auth.db')
    monkeypatch.setattr(auth, 'AUTH_DB_PATH', path)
    monkeypatch.setenv('GUI_AUTH_ENABLED', 'true')

    def _pbkdf2_hash(password, **kwargs):
        return werkzeug.security.generate_password_hash(password, method='pbkdf2:sha256')

    monkeypatch.setattr(auth, 'generate_password_hash', _pbkdf2_hash)
    return path


@pytest.fixture()
def app_client(tmp_path, monkeypatch, pykms_src):
    db = tmp_path / 'kms.db'
    with sqlite3.connect(db) as con:
        con.execute(
            'CREATE TABLE clients(clientMachineId TEXT, machineName TEXT, applicationId TEXT, '
            'skuId TEXT, licenseStatus TEXT, lastRequestTime INTEGER, kmsEpid TEXT, '
            'requestCount INTEGER, lastRequestIP TEXT, PRIMARY KEY(clientMachineId, applicationId))'
        )

    monkeypatch.setenv('GUI_AUTH_ENABLED', 'false')
    monkeypatch.setenv('ADMIN_PUBLIC', 'false')
    monkeypatch.setenv('PYKMS_SQLITE_DB_PATH', str(db))
    monkeypatch.setenv('GUI_AUTH_DB_PATH', str(tmp_path / 'auth.db'))
    monkeypatch.setenv('GUI_SECRET_KEY', 'test-secret-key-for-pytest-only')
    monkeypatch.setenv('KMS_POLICY_FILE', str(tmp_path / 'kms-policy.json'))
    monkeypatch.setenv('GUI_AUDIT_DB_PATH', str(tmp_path / 'audit.db'))
    monkeypatch.setenv('PYKMS_LICENSE_PATH', str(pykms_src.parent / 'LICENSE'))
    monkeypatch.setenv('PYKMS_VERSION_PATH', str(tmp_path / 'VERSION'))
    (tmp_path / 'VERSION').write_text('test\n', encoding='utf-8')

    _purge_pykms_modules()
    from pykms_app import create_app

    app = create_app()
    app.config['TESTING'] = True
    return app.test_client()
