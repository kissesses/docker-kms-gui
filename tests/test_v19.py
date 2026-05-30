import io
import json
import tarfile

import pytest


def test_filter_clients_by_app_and_query():
    from pykms_services import filter_clients

    clients = [
        {'machineName': 'PC-1', 'applicationId': 'Windows', 'licenseStatus': 'Activated', 'clientMachineId': 'a'},
        {'machineName': 'Office-1', 'applicationId': 'Office', 'licenseStatus': 'Activated', 'clientMachineId': 'b'},
    ]
    assert len(filter_clients(clients, application='Windows')) == 1
    assert len(filter_clients(clients, query='office-1')) == 1


def test_filter_clients_by_health(monkeypatch, tmp_path):
    import os
    import time

    monkeypatch.setenv('KMS_POLICY_FILE', str(tmp_path / 'kms-policy.json'))
    (tmp_path / 'kms-policy.json').write_text(
        json.dumps({
            'client_count': 26,
            'activation_interval_minutes': 120,
            'renewal_interval_minutes': 10080,
            'hwid': 'RANDOM',
            'port': 1688,
            'host': 'kms',
            'licensing_validity_days': 180,
        }),
        encoding='utf-8',
    )
    from pykms_services import filter_clients

    now = int(time.time())
    clients = [{
        'machineName': 'Old',
        'applicationId': 'Windows',
        'licenseStatus': 'Activated',
        'lastRequestTime': now - 999999,
        'clientMachineId': 'x',
    }]
    assert len(filter_clients(clients, health='overdue')) == 1
    assert len(filter_clients(clients, health='healthy')) == 0


def test_backup_roundtrip(tmp_path, monkeypatch):
    import sqlite3

    var = tmp_path / 'var'
    var.mkdir()
    db = var / 'kms.db'
    with sqlite3.connect(db) as con:
        con.execute('CREATE TABLE t(id INTEGER)')
    policy = var / 'kms-policy.json'
    policy.write_text('{"client_count": 26}', encoding='utf-8')

    monkeypatch.setenv('PYKMS_SQLITE_DB_PATH', str(db))
    monkeypatch.setenv('KMS_POLICY_FILE', str(policy))
    monkeypatch.setenv('GUI_AUTH_DB_PATH', str(var / 'gui_auth.db'))
    monkeypatch.setenv('GUI_AUDIT_DB_PATH', str(var / 'gui_audit.db'))
    monkeypatch.setenv('GUI_SECRET_FILE', str(var / '.gui_secret'))

    from tests.helpers import purge_pykms_modules
    purge_pykms_modules()
    import pykms_backup as backup

    archive = backup.create_archive()
    assert archive.getbuffer().nbytes > 0

    db.write_text('replaced', encoding='utf-8')
    backup.restore_archive(io.BytesIO(archive.getvalue()))
    with sqlite3.connect(db) as con:
        con.execute('SELECT 1 FROM t').fetchone()


def test_webhook_new_client(monkeypatch, tmp_path):
    monkeypatch.setenv('PYKMS_SQLITE_DB_PATH', str(tmp_path / 'kms.db'))
    monkeypatch.setenv('WEBHOOK_URL', 'http://127.0.0.1:9/hook')
    monkeypatch.setenv('WEBHOOK_EVENTS', 'client_new')

    from tests.helpers import purge_pykms_modules
    purge_pykms_modules()
    import pykms_webhook as webhook

    sent = []
    monkeypatch.setattr(webhook, 'send_event', lambda event, payload: sent.append(event) or True)

    clients = [{'clientMachineId': 'abc', 'applicationId': 'Windows', 'machineName': 'PC', 'licenseStatus': 'Activated'}]
    result = webhook.check_and_notify(clients)
    assert result['sent'] == 1
    assert sent == ['client_new']
    result2 = webhook.check_and_notify(clients)
    assert result2['sent'] == 0


def test_ops_disabled_without_docker(monkeypatch):
    monkeypatch.delenv('OPS_DOCKER_ENABLED', raising=False)
    from pykms_ops import docker_enabled, restart_kms_container

    assert docker_enabled() is False
    with pytest.raises(RuntimeError):
        restart_kms_container()
