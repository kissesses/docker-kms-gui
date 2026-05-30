"""Runtime diagnostics for GUI stability troubleshooting."""

import os
import time

from pykms_config import config

SUPERVISOR_LOG = os.path.join(
    os.path.dirname(config.DB_PATH),
    'gui-supervisor.log',
)


def _read_meminfo():
    try:
        with open('/proc/meminfo', 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
        data = {}
        for line in lines:
            if ':' not in line:
                continue
            key, val = line.split(':', 1)
            data[key.strip()] = val.strip()
        return data
    except OSError:
        return {}


def _kb_to_mb(raw):
    try:
        return round(int(str(raw).split()[0]) / 1024, 1)
    except (ValueError, IndexError, TypeError):
        return None


def memory_snapshot():
    info = _read_meminfo()
    if not info:
        return {'available': False}
    total = _kb_to_mb(info.get('MemTotal'))
    avail = _kb_to_mb(info.get('MemAvailable'))
    used = round(total - avail, 1) if total is not None and avail is not None else None
    return {
        'available': True,
        'total_mb': total,
        'available_mb': avail,
        'used_mb': used,
        'swap_free_mb': _kb_to_mb(info.get('SwapFree')),
    }


def process_rss_mb():
    try:
        with open('/proc/self/status', 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('VmRSS:'):
                    return _kb_to_mb(line.split(':', 1)[1].strip())
    except OSError:
        pass
    return None


def tail_supervisor_log(limit=40):
    if not os.path.isfile(SUPERVISOR_LOG):
        return []
    try:
        with open(SUPERVISOR_LOG, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.read().splitlines()
        return lines[-limit:]
    except OSError:
        return []


def var_files():
    var_dir = os.path.dirname(config.DB_PATH)
    names = (
        'kms.db',
        'gui_auth.db',
        'gui_audit.db',
        'kms-policy.json',
        'gui-supervisor.log',
        '.webhook_state.json',
        '.gui_secret',
    )
    rows = []
    for name in names:
        path = os.path.join(var_dir, name)
        rows.append({
            'name': name,
            'exists': os.path.isfile(path),
            'size': os.path.getsize(path) if os.path.isfile(path) else 0,
        })
    return rows


def gunicorn_config():
    return {
        'workers': os.environ.get('GUNICORN_WORKERS', '1'),
        'threads': os.environ.get('GUNICORN_THREADS', '2'),
        'preload': os.environ.get('GUNICORN_PRELOAD', 'false'),
        'max_requests': os.environ.get('GUNICORN_MAX_REQUESTS', '0'),
        'timeout': os.environ.get('GUNICORN_TIMEOUT', '120'),
    }


def recommendations(mem, restart_count):
    tips = []
    if mem.get('available') and mem.get('available_mb') is not None:
        if mem['available_mb'] < 128:
            tips.append('Low RAM (<128 MB free): set GUNICORN_PRELOAD=false, GUNICORN_THREADS=2, add swap or use 2 GB+ VPS.')
    if restart_count and restart_count > 0:
        tips.append('Gunicorn restarted in this container lifetime — check gui-supervisor.log and host dmesg for OOM kills.')
    if os.environ.get('GUNICORN_PRELOAD', 'false').lower() in ('1', 'true', 'yes'):
        tips.append('GUNICORN_PRELOAD=true increases memory use on small VPS — try GUNICORN_PRELOAD=false.')
    if not tips:
        tips.append('If outages persist: docker compose logs gui --tail 200 and dmesg | grep -i oom on the host.')
    return tips


def restart_count():
    count = 0
    for line in tail_supervisor_log(500):
        if 'gunicorn exited' in line or 'exit code' in line:
            count += 1
    return count


def build_report():
    from pykms_services import uptime_seconds

    mem = memory_snapshot()
    restarts = restart_count()
    return {
        'uptime_seconds': uptime_seconds(),
        'memory': mem,
        'process_rss_mb': process_rss_mb(),
        'gunicorn': gunicorn_config(),
        'supervisor_log_tail': tail_supervisor_log(),
        'restart_events': restarts,
        'var_files': var_files(),
        'recommendations': recommendations(mem, restarts),
        'webhook_enabled': bool(os.environ.get('WEBHOOK_URL', '').strip()),
    }
