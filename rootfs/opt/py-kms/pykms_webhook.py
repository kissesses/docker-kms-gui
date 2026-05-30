"""Outbound webhook notifications for client events."""

import json
import os
import subprocess
import time
import urllib.error
import urllib.request

import pykms_activation as activation

STATE_FILE = os.path.join(
    os.path.dirname(os.environ.get('PYKMS_SQLITE_DB_PATH', '/kms/var/kms.db')),
    '.webhook_state.json',
)
UNHEALTHY = frozenset({'due_soon', 'overdue', 'at_risk'})


def configured():
    return bool(os.environ.get('WEBHOOK_URL', '').strip())


def _events_enabled():
    raw = os.environ.get('WEBHOOK_EVENTS', 'client_new,client_unhealthy')
    return {e.strip() for e in raw.split(',') if e.strip()}


def _load_state():
    if not os.path.isfile(STATE_FILE):
        return {'clients': {}, 'unhealthy': {}}
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict):
                data.setdefault('clients', {})
                data.setdefault('unhealthy', {})
                return data
    except (OSError, json.JSONDecodeError):
        pass
    return {'clients': {}, 'unhealthy': {}}


def _save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE) or '.', exist_ok=True)
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)
        f.write('\n')


def _client_key(client):
    return f"{client.get('clientMachineId', '')}:{client.get('applicationId', '')}"


def _post_payload(event, payload):
    url = os.environ.get('WEBHOOK_URL', '').strip()
    if not url:
        return False
    body = json.dumps({
        'event': event,
        'timestamp': int(time.time()),
        'data': payload,
    }).encode('utf-8')
    headers = {'Content-Type': 'application/json', 'User-Agent': 'kms-gui-webhook/1.9'}
    secret = os.environ.get('WEBHOOK_SECRET', '').strip()
    if secret:
        headers['X-Webhook-Secret'] = secret
    req = urllib.request.Request(url, data=body, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return 200 <= resp.status < 300
    except urllib.error.URLError:
        return False


def _curl_post(event, payload):
    url = os.environ.get('WEBHOOK_URL', '').strip()
    if not url:
        return False
    body = json.dumps({
        'event': event,
        'timestamp': int(time.time()),
        'data': payload,
    })
    cmd = [
        'curl', '-fsS', '-X', 'POST', url,
        '-H', 'Content-Type: application/json',
        '-H', 'User-Agent: kms-gui-webhook/1.9',
        '--max-time', '15',
        '-d', body,
    ]
    secret = os.environ.get('WEBHOOK_SECRET', '').strip()
    if secret:
        cmd.extend(['-H', f'X-Webhook-Secret: {secret}'])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    return result.returncode == 0


def send_event(event, payload):
    if _curl_post(event, payload):
        return True
    return _post_payload(event, payload)


def check_and_notify(clients=None):
    if not configured():
        return {'sent': 0}
    from pykms_services import load_clients

    events = _events_enabled()
    if clients is None:
        clients = load_clients()
    policy = activation.load_policy()
    now = int(time.time())
    state = _load_state()
    sent = 0

    current_keys = {}
    for client in clients or []:
        key = _client_key(client)
        if not key or key == ':':
            continue
        current_keys[key] = True
        row = activation.enrich_client(client, policy, now)

        if 'client_new' in events and key not in state['clients']:
            if send_event('client_new', {
                'clientMachineId': client.get('clientMachineId'),
                'applicationId': client.get('applicationId'),
                'machineName': client.get('machineName'),
                'machineIp': client.get('machineIp') or client.get('lastRequestIP'),
                'licenseStatus': client.get('licenseStatus'),
            }):
                sent += 1
            state['clients'][key] = int(time.time())

        health = row.get('health')
        if 'client_unhealthy' in events and health in UNHEALTHY:
            prev = state['unhealthy'].get(key)
            if prev != health:
                if send_event('client_unhealthy', {
                    'clientMachineId': client.get('clientMachineId'),
                    'applicationId': client.get('applicationId'),
                    'machineName': client.get('machineName'),
                    'health': health,
                    'health_note': row.get('health_note'),
                    'licenseStatus': client.get('licenseStatus'),
                }):
                    sent += 1
                state['unhealthy'][key] = health
        elif key in state['unhealthy'] and health not in UNHEALTHY:
            del state['unhealthy'][key]

    for key in list(state['clients']):
        if key not in current_keys:
            del state['clients'][key]
    for key in list(state['unhealthy']):
        if key not in current_keys:
            del state['unhealthy'][key]

    _save_state(state)
    return {'sent': sent, 'tracked': len(current_keys)}
