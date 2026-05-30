"""Flask application factory."""

import datetime
import os
import secrets
import time

from flask import Flask

import pykms_auth as auth
import pykms_csrf as csrf
import pykms_i18n as i18n
from pykms_config import config
from pykms_services import load_version_info

from pykms_routes_auth import auth_bp
from pykms_routes_pages import pages_bp
from pykms_routes_admin import admin_bp
from pykms_routes_api import api_bp


def _load_secret_key():
    env_key = os.environ.get('GUI_SECRET_KEY')
    if env_key:
        return env_key
    path = config.SECRET_FILE
    if os.path.isfile(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    key = secrets.token_hex(32)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(key)
        os.chmod(path, 0o600)
    except OSError:
        pass
    return key


def create_app():
    app = Flask('pykms_webui')
    app.secret_key = _load_secret_key()
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=config.TLS_ENABLED,
        PERMANENT_SESSION_LIFETIME=datetime.timedelta(days=7),
    )

    app.jinja_env.globals['version_info'] = load_version_info()
    app.jinja_env.globals['start_time'] = datetime.datetime.now()

    app.register_blueprint(auth_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    @app.context_processor
    def inject():
        from flask import request
        from pykms_routes_auth import current_user
        user = current_user()
        ctx = {
            'path': request.path,
            'auth_enabled': auth.is_enabled(),
            'admin_public': config.ADMIN_PUBLIC,
            'current_user': user,
            'setup_required': auth.is_enabled() and not auth.is_setup_complete(),
            'show_admin_nav': (
                (auth.is_enabled() and user)
                or (not auth.is_enabled() and config.ADMIN_PUBLIC)
            ),
        }
        ctx.update(csrf.inject())
        ctx.update(i18n.inject())
        return ctx

    @app.before_request
    def _request_timer():
        from flask import g
        g._req_start = time.time()

    @app.after_request
    def _log_slow_request(response):
        from flask import g, request
        start = getattr(g, '_req_start', None)
        if start is not None:
            from pykms_slowlog import log_slow
            log_slow(request.method, request.path, (time.time() - start) * 1000, response.status_code)
        return response

    @app.before_request
    def guard():
        from flask import jsonify, request, redirect, url_for, session
        from pykms_routes_auth import current_user
        path = request.path

        if path.startswith('/admin') and not auth.is_enabled() and not config.ADMIN_PUBLIC:
            return redirect(url_for('pages.dashboard'))

        if path.startswith('/api/'):
            if auth.api_protection_enabled():
                if not auth.verify_api_bearer() and not current_user():
                    return jsonify({'error': 'Unauthorized'}), 401
            return None

        if not auth.is_enabled():
            return None
        if path.startswith('/static/'):
            return None
        if path in ('/livez', '/readyz', '/login', '/setup'):
            return None
        if not auth.is_setup_complete():
            if path != '/setup':
                return redirect(url_for('auth.setup_page'))
            return None
        if path == '/setup':
            return redirect(url_for('pages.dashboard'))
        if 'user_id' not in session:
            if path == '/login':
                return None
            nxt = path if path != '/' else None
            return redirect(url_for('auth.login_page', next=nxt))
        return None

    return app


def _start_webhook_worker(app):
    import os
    import threading
    import time

    if not os.environ.get('WEBHOOK_URL', '').strip():
        return

    def _loop():
        import pykms_webhook as webhook
        while True:
            time.sleep(int(os.environ.get('WEBHOOK_INTERVAL', '60')))
            with app.app_context():
                try:
                    webhook.check_and_notify()
                except Exception:
                    pass

    threading.Thread(target=_loop, daemon=True, name='webhook-worker').start()


app = create_app()
_start_webhook_worker(app)
