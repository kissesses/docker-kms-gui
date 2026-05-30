import time

import pykms_activation as activation
import pytest


@pytest.fixture()
def policy_file(tmp_path, monkeypatch):
    path = str(tmp_path / 'kms-policy.json')
    monkeypatch.setattr(activation, 'POLICY_FILE', path)
    return path


def test_save_and_load_policy(policy_file):
    saved = activation.save_policy('30', '120', '10080', 'RANDOM')
    assert saved['client_count'] == 30
    assert saved['pending_kms_restart'] is True
    loaded = activation.load_policy()
    assert loaded['client_count'] == 30


def test_health_activated_client(monkeypatch):
    now = int(time.time())
    policy = {
        'client_count': 26,
        'activation_interval_minutes': 120,
        'renewal_interval_minutes': 10080,
        'hwid': 'RANDOM',
        'port': 1688,
        'host': 'kms',
        'licensing_validity_days': 180,
    }
    client = {
        'clientMachineId': 'x',
        'machineName': 'PC',
        'machineIp': '1.1.1.1',
        'applicationId': 'Windows',
        'licenseStatus': 'Activated',
        'lastRequestTime': now - 3600,
        'kmsEpid': 'e',
        'requestCount': 1,
    }
    row = activation.enrich_client(client, policy, now)
    assert row['health'] == 'healthy'


def test_iso_last_request_time():
    from pykms_time import parse_ts

    iso = '2026-05-30T20:18:39'
    base = parse_ts(iso)
    assert base is not None
    policy = {
        'client_count': 26,
        'activation_interval_minutes': 120,
        'renewal_interval_minutes': 10080,
        'hwid': 'RANDOM',
        'port': 1688,
        'host': 'kms',
        'licensing_validity_days': 180,
    }
    client = {
        'clientMachineId': 'x',
        'machineName': 'PC',
        'applicationId': 'Windows',
        'licenseStatus': 'Activated',
        'lastRequestTime': iso,
        'kmsEpid': 'e',
        'requestCount': 1,
    }
    row = activation.enrich_client(client, policy, base + 3600)
    assert row['health'] == 'healthy'
    assert row['last_seen_fmt'] != 'Never'
