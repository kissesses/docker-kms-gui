"""Operational helpers: Docker KMS restart, ops status."""

import json
import os
import subprocess


def docker_enabled():
    return (
        os.environ.get('OPS_DOCKER_ENABLED', 'false').lower() in ('1', 'true', 'yes')
        and os.path.exists('/var/run/docker.sock')
    )


def _docker_request(method, path, timeout=30):
    cmd = [
        'curl', '-sS', '--unix-socket', '/var/run/docker.sock',
        '-X', method,
        f'http://localhost{path}',
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or 'Docker API request failed')
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)


def _resolve_kms_container_name():
    explicit = os.environ.get('KMS_CONTAINER_NAME', '').strip()
    if explicit:
        return explicit.lstrip('/')

    filters = json.dumps({'label': ['com.docker.compose.service=kms']})
    containers = _docker_request('GET', f'/containers/json?all=false&filters={filters}')
    if not containers:
        raise RuntimeError('KMS container not found (set KMS_CONTAINER_NAME or mount docker.sock)')
    name = containers[0]['Names'][0].lstrip('/')
    return name


def restart_kms_container(timeout=60):
    if not docker_enabled():
        raise RuntimeError('Docker ops disabled (set OPS_DOCKER_ENABLED=true and mount docker.sock)')
    name = _resolve_kms_container_name()
    _docker_request('POST', f'/containers/{name}/restart?t={timeout}', timeout=timeout + 5)
    return name


def ops_status():
    status = {
        'docker_enabled': docker_enabled(),
        'kms_container': None,
        'kms_running': False,
        'webhook_configured': bool(os.environ.get('WEBHOOK_URL', '').strip()),
    }
    if not status['docker_enabled']:
        return status
    try:
        name = _resolve_kms_container_name()
        status['kms_container'] = name
        info = _docker_request('GET', f'/containers/{name}/json')
        status['kms_running'] = info.get('State', {}).get('Running', False)
    except Exception as e:
        status['error'] = str(e)
    return status
