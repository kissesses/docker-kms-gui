"""Slow request logging."""

import os
import time

SLOW_LOG = os.environ.get('GUI_SLOW_LOG', '/kms/var/gui-slow.log')
SLOW_THRESHOLD = float(os.environ.get('GUI_SLOW_THRESHOLD', '2.0'))


def log_slow(method, path, duration_ms, status):
    if duration_ms < SLOW_THRESHOLD * 1000:
        return
    try:
        os.makedirs(os.path.dirname(SLOW_LOG) or '.', exist_ok=True)
        stamp = time.strftime('%Y-%m-%d %H:%M:%S')
        with open(SLOW_LOG, 'a', encoding='utf-8') as handle:
            handle.write(f'{stamp} {method} {path} {duration_ms:.0f}ms status={status}\n')
    except OSError:
        pass


def tail_slow_log(limit=50):
    if not os.path.isfile(SLOW_LOG):
        return []
    try:
        with open(SLOW_LOG, 'r', encoding='utf-8', errors='replace') as handle:
            lines = handle.read().splitlines()
        return lines[-limit:]
    except OSError:
        return []
