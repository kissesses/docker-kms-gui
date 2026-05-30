"""Gunicorn configuration — worker timeout logging and defaults."""

import os

bind = os.environ.get('GUNICORN_BIND', '127.0.0.1:8080')
workers = int(os.environ.get('GUNICORN_WORKERS', '2'))
threads = int(os.environ.get('GUNICORN_THREADS', '2'))
timeout = int(os.environ.get('GUNICORN_TIMEOUT', '300'))
graceful_timeout = int(os.environ.get('GUNICORN_GRACEFUL_TIMEOUT', '30'))
worker_class = 'gthread'
user = os.environ.get('APP_UID', '1000')
group = 'kms'
loglevel = os.environ.get('LOG_LEVEL', os.environ.get('GUNICORN_LOG_LEVEL', 'INFO'))
accesslog = '-'
errorlog = '-'
capture_output = True
keepalive = int(os.environ.get('GUNICORN_KEEPALIVE', '5'))

_max_requests = int(os.environ.get('GUNICORN_MAX_REQUESTS', '0'))
if _max_requests > 0:
    max_requests = _max_requests
    max_requests_jitter = 100

preload_app = os.environ.get('GUNICORN_PRELOAD', 'false').lower() in ('1', 'true', 'yes')

SUPERVISOR_LOG = os.environ.get('GUI_SUPERVISOR_LOG', '/kms/var/gui-supervisor.log')
SLOW_LOG = os.environ.get('GUI_SLOW_LOG', '/kms/var/gui-slow.log')


def _append_log(path, message):
    try:
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        with open(path, 'a', encoding='utf-8') as handle:
            handle.write(message.rstrip() + '\n')
    except OSError:
        pass


def worker_abort(worker):
    _append_log(
        SUPERVISOR_LOG,
        f'[gunicorn] WORKER TIMEOUT pid={worker.pid} — request exceeded {timeout}s (master still running)',
    )


def worker_int(worker):
    _append_log(SUPERVISOR_LOG, f'[gunicorn] worker interrupted pid={worker.pid}')


def child_exit(server, worker):
    _append_log(
        SUPERVISOR_LOG,
        f'[gunicorn] worker exited pid={worker.pid} age={getattr(worker, "age", "?")}',
    )
