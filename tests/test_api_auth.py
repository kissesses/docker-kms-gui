import pytest

from tests.helpers import purge_pykms_modules


@pytest.fixture()
def protected_app(tmp_path, monkeypatch, pykms_src):
    import os
    import sqlite3

    db = tmp_path / 'kms.db'
    with sqlite3.connect(db) as con:
        con.execute(
            'CREATE TABLE clients(clientMachineId TEXT, machineName TEXT, applicationId TEXT, '
            'skuId TEXT, licenseStatus TEXT, lastRequestTime INTEGER, kmsEpid TEXT, '
            'requestCount INTEGER, lastRequestIP TEXT, PRIMARY KEY(clientMachineId, applicationId))'
        )

    monkeypatch.setenv('GUI_AUTH_ENABLED', 'true')
    monkeypatch.setenv('INTERNET_MODE', 'true')
    monkeypatch.setenv('ADMIN_PUBLIC', 'false')
    monkeypatch.setenv('PYKMS_SQLITE_DB_PATH', str(db))
    monkeypatch.setenv('GUI_AUTH_DB_PATH', str(tmp_path / 'auth.db'))
    monkeypatch.setenv('GUI_SECRET_KEY', 'test-secret-key-for-pytest-only')
    monkeypatch.setenv('KMS_POLICY_FILE', str(tmp_path / 'kms-policy.json'))
    monkeypatch.setenv('GUI_AUDIT_DB_PATH', str(tmp_path / 'audit.db'))
    license_path = os.path.join(os.path.dirname(str(pykms_src)), 'LICENSE')
    if not os.path.isfile(license_path):
        license_path = str(pykms_src)
    monkeypatch.setenv('PYKMS_LICENSE_PATH', license_path)
    monkeypatch.setenv('PYKMS_VERSION_PATH', str(tmp_path / 'VERSION'))
    (tmp_path / 'VERSION').write_text('test\nref\n', encoding='utf-8')

    purge_pykms_modules()
    from pykms_app import create_app

    app = create_app()
    app.config['TESTING'] = True
    return app.test_client()


def test_api_unauthorized_when_protected(protected_app):
    rv = protected_app.get('/api/v1/stats')
    assert rv.status_code == 401
    assert rv.is_json


def test_api_bearer_token(monkeypatch):
    from flask import Flask

    monkeypatch.setenv('GUI_API_TOKEN', 'test-api-token-secret')
    purge_pykms_modules()
    import pykms_auth as auth

    app = Flask(__name__)
    with app.test_request_context(headers={'Authorization': 'Bearer test-api-token-secret'}):
        assert auth.verify_api_bearer() is True
    with app.test_request_context(headers={'Authorization': 'Bearer wrong'}):
        assert auth.verify_api_bearer() is False


def test_livez_public_when_protected(protected_app):
    rv = protected_app.get('/livez')
    assert rv.status_code == 200
