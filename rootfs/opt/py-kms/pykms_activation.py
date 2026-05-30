"""KMS activation policy and client renewal insights for the admin panel."""

import json
import os
import time

from pykms_services import format_ts, parse_ts

POLICY_FILE = os.environ.get('KMS_POLICY_FILE', '/kms/var/kms-policy.json')
LICENSING_VALIDITY_DAYS = 180


def _env_int(name, default):
    raw = os.environ.get(name)
    if raw is None or raw == '':
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def load_policy():
    if os.path.isfile(POLICY_FILE):
        try:
            with open(POLICY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return _normalize_policy(data)
        except (OSError, json.JSONDecodeError):
            pass
    return _normalize_policy({
        'client_count': _env_int('KMS_CLIENT_COUNT', _env_int('CLIENT_COUNT', 26)),
        'activation_interval_minutes': _env_int(
            'KMS_ACTIVATION_INTERVAL', _env_int('ACTIVATION_INTERVAL', 120),
        ),
        'renewal_interval_minutes': _env_int(
            'KMS_RENEWAL_INTERVAL', _env_int('RENEWAL_INTERVAL', 10080),
        ),
        'hwid': os.environ.get('KMS_HWID', os.environ.get('HWID', 'RANDOM')),
        'port': _env_int('KMS_PORT', _env_int('PORT', 1688)),
        'host': os.environ.get('KMS_HOST', 'kms'),
        'licensing_validity_days': LICENSING_VALIDITY_DAYS,
    })


def _normalize_policy(data):
    return {
        'client_count': int(data.get('client_count', 26)),
        'activation_interval_minutes': int(data.get('activation_interval_minutes', 120)),
        'renewal_interval_minutes': int(data.get('renewal_interval_minutes', 10080)),
        'hwid': str(data.get('hwid', 'RANDOM')),
        'port': int(data.get('port', 1688)),
        'host': str(data.get('host', 'kms')),
        'licensing_validity_days': int(data.get('licensing_validity_days', LICENSING_VALIDITY_DAYS)),
        'updated_at': parse_ts(data.get('updated_at')),
        'pending_kms_restart': bool(data.get('pending_kms_restart', False)),
    }


def save_policy(client_count, activation_interval_minutes, renewal_interval_minutes, hwid=None):
    if client_count < 1 or client_count > 9999:
        raise ValueError('Client count must be 1–9999')
    if activation_interval_minutes < 15 or activation_interval_minutes > 43200:
        raise ValueError('Activation interval must be 15–43200 minutes')
    if renewal_interval_minutes < 15 or renewal_interval_minutes > 43200:
        raise ValueError('Renewal interval must be 15–43200 minutes')
    policy = load_policy()
    policy['client_count'] = int(client_count)
    policy['activation_interval_minutes'] = int(activation_interval_minutes)
    policy['renewal_interval_minutes'] = int(renewal_interval_minutes)
    if hwid:
        policy['hwid'] = str(hwid).strip() or 'RANDOM'
    policy['updated_at'] = int(time.time())
    policy['pending_kms_restart'] = True
    os.makedirs(os.path.dirname(POLICY_FILE) or '.', exist_ok=True)
    with open(POLICY_FILE, 'w', encoding='utf-8') as f:
        json.dump(policy, f, indent=2)
        f.write('\n')
    return _normalize_policy(policy)


def format_duration(minutes):
    if minutes is None:
        return 'N/A'
    minutes = int(minutes)
    if minutes < 60:
        return f'{minutes} min'
    if minutes < 1440:
        hours = minutes / 60
        return f'{hours:.1f} h' if minutes % 60 else f'{minutes // 60} h'
    days = minutes / 1440
    return f'{days:.1f} d' if minutes % 1440 else f'{minutes // 1440} d'


def _health_status(client, policy, now):
    status = (client.get('licenseStatus') or '').strip()
    last = parse_ts(client.get('lastRequestTime'))
    if last is None:
        return 'unknown', 'No contact recorded'

    age_min = max(0, (now - last) / 60)
    renewal_min = policy['renewal_interval_minutes']
    activation_min = policy['activation_interval_minutes']

    if status == 'Activated':
        if age_min <= renewal_min * 0.85:
            return 'healthy', 'Within renewal window'
        if age_min <= renewal_min * 1.1:
            return 'due_soon', 'Renewal check expected soon'
        return 'overdue', 'Past expected renewal interval'

    if status == 'Notifications Mode':
        if age_min <= activation_min * 2:
            return 'grace', 'Grace period — activation pending'
        return 'at_risk', 'Extended grace — client may deactivate'

    return 'unknown', status or 'Unknown status'


def enrich_client(client, policy, now=None):
    now = now or int(time.time())
    last = parse_ts(client.get('lastRequestTime'))
    renewal_sec = policy['renewal_interval_minutes'] * 60
    activation_sec = policy['activation_interval_minutes'] * 60

    next_renewal = last + renewal_sec if last is not None else None
    next_activation = last + activation_sec if last is not None else None
    license_horizon = last + policy['licensing_validity_days'] * 86400 if last is not None else None

    age_min = max(0, (now - last) / 60) if last is not None else None
    health, health_note = _health_status(client, policy, now)

    app_id = client.get('applicationId', '')
    if app_id == 'Windows':
        min_clients = 25
    else:
        min_clients = 5

    return {
        **client,
        'last_seen_fmt': format_ts(last),
        'next_renewal_ts': next_renewal,
        'next_renewal_fmt': format_ts(next_renewal),
        'next_activation_fmt': format_ts(next_activation),
        'license_horizon_fmt': format_ts(license_horizon),
        'minutes_since_contact': int(age_min) if age_min is not None else None,
        'since_contact_fmt': format_duration(age_min),
        'health': health,
        'health_note': health_note,
        'binding_label': client.get('machineName') or 'Unknown host',
        'binding_target': f"KMS :{policy['port']}",
        'binding_epid': client.get('kmsEpid') or 'N/A',
        'min_client_threshold': min_clients,
        'threshold_met': policy['client_count'] >= min_clients,
    }


def build_activation_overview(clients, policy=None, now=None):
    now = now or int(time.time())
    policy = policy or load_policy()
    enriched = [enrich_client(c, policy, now) for c in (clients or [])]

    health_counts = {
        'healthy': 0,
        'due_soon': 0,
        'overdue': 0,
        'grace': 0,
        'at_risk': 0,
        'unknown': 0,
    }
    for row in enriched:
        health_counts[row['health']] = health_counts.get(row['health'], 0) + 1

    windows = sum(1 for c in enriched if c.get('applicationId') == 'Windows')
    office = len(enriched) - windows

    return {
        'policy': {
            **policy,
            'activation_interval_fmt': format_duration(policy['activation_interval_minutes']),
            'renewal_interval_fmt': format_duration(policy['renewal_interval_minutes']),
            'updated_at_fmt': format_ts(policy.get('updated_at')) if policy.get('updated_at') else 'From environment',
            'client_threshold_windows': 25,
            'client_threshold_office': 5,
            'threshold_windows_met': policy['client_count'] >= 25,
            'threshold_office_met': policy['client_count'] >= 5,
            'pending_kms_restart': policy.get('pending_kms_restart', False),
        },
        'clients': enriched,
        'summary': {
            'total': len(enriched),
            'windows': windows,
            'office': office,
            'activated': sum(1 for c in enriched if c.get('licenseStatus') == 'Activated'),
            'grace': sum(1 for c in enriched if c.get('licenseStatus') == 'Notifications Mode'),
            **health_counts,
        },
    }
