import csv
import io
import os
import secrets
import uuid
import datetime

from flask import (
    Flask, jsonify, render_template, Response,
    request, redirect, url_for, session, flash,
)

import pykms_auth as auth
from pykms_Sql import sql_get_all
from pykms_DB2Dict import kmsDB2Dict


def _random_uuid():
    return str(uuid.uuid4()).replace('-', '_')


_serve_count = 0


def _increase_serve_count():
    global _serve_count
    _serve_count += 1


def _get_serve_count():
    return _serve_count


_kms_items = None
_kms_items_noglvk = None


def _get_kms_items_cache():
    global _kms_items, _kms_items_noglvk
    if _kms_items is None:
        _kms_items = {}
        _kms_items_noglvk = 0
        for section in kmsDB2Dict():
            for element in section:
                if "KmsItems" in element:
                    for product in element["KmsItems"]:
                        group_name = product["DisplayName"]
                        items = {}
                        for item in product["SkuItems"]:
                            items[item["DisplayName"]] = item["Gvlk"]
                            if not item["Gvlk"]:
                                _kms_items_noglvk += 1
                        if len(items) == 0:
                            continue
                        if group_name not in _kms_items:
                            _kms_items[group_name] = {}
                        _kms_items[group_name].update(items)
                elif "DisplayName" in element and "BuildNumber" in element and "PlatformId" in element:
                    pass
                elif "DisplayName" in element and "Activate" in element:
                    pass
                else:
                    raise NotImplementedError(f'Unknown element: {element}')
    return _kms_items, _kms_items_noglvk


def _load_secret_key():
    env_key = os.environ.get('GUI_SECRET_KEY')
    if env_key:
        return env_key
    path = os.environ.get('GUI_SECRET_FILE', '/kms/var/.gui_secret')
    if os.path.isfile(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    key = secrets.token_hex(32)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(key)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return key


app = Flask('pykms_webui')
app.secret_key = _load_secret_key()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get('NGINX_TLS_ENABLED', 'false').lower() == 'true',
    PERMANENT_SESSION_LIFETIME=datetime.timedelta(days=7),
)

app.jinja_env.globals['start_time'] = datetime.datetime.now()
app.jinja_env.globals['get_serve_count'] = _get_serve_count
app.jinja_env.globals['random_uuid'] = _random_uuid
app.jinja_env.globals['version_info'] = None

_version_info_path = os.environ.get('PYKMS_VERSION_PATH', '../VERSION')
if os.path.exists(_version_info_path):
    with open(_version_info_path, 'r') as f:
        app.jinja_env.globals['version_info'] = {
            'hash': f.readline().strip(),
            'reference': f.readline().strip()
        }

_dbEnvVarName = 'PYKMS_SQLITE_DB_PATH'

_PUBLIC_PATHS = frozenset(['/livez', '/readyz', '/login', '/setup'])


def _env_check():
    if _dbEnvVarName not in os.environ:
        raise Exception(f'Environment variable is not set: {_dbEnvVarName}')


def _get_db_path():
    return os.environ.get(_dbEnvVarName)


def _load_clients():
    db_path = _get_db_path()
    if not db_path:
        raise Exception(f'Environment variable is not set: {_dbEnvVarName}')
    clients = sql_get_all(db_path)
    if clients:
        for client in clients:
            if 'machineIp' not in client and 'lastRequestIP' in client:
                client['machineIp'] = client['lastRequestIP']
    return clients


def _client_counts(clients):
    if not clients:
        return 0, 0, 0
    total = len(clients)
    windows = len([c for c in clients if c['applicationId'] == 'Windows'])
    office = total - windows
    return total, windows, office


def _product_counts():
    items, noglvk = _get_kms_items_cache()
    count_products = sum([len(entries) for entries in items.values()])
    count_windows = sum([len(entries) for (name, entries) in items.items() if 'windows' in name.lower()])
    count_office = sum([len(entries) for (name, entries) in items.items() if 'office' in name.lower()])
    return items, noglvk, count_products, count_windows, count_office


def _uptime_seconds():
    return int((datetime.datetime.now() - app.jinja_env.globals['start_time']).total_seconds())


def _format_ts(ts):
    if not ts:
        return 'Never'
    return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')


def _build_stats(clients=None):
    if clients is None:
        try:
            clients = _load_clients()
        except Exception:
            clients = None
    count_clients, count_windows, count_office = _client_counts(clients)
    _, noglvk, count_products, count_products_windows, count_products_office = _product_counts()
    version = app.jinja_env.globals.get('version_info') or {}
    return {
        'uptime_seconds': _uptime_seconds(),
        'serve_count': _get_serve_count(),
        'count_clients': count_clients,
        'count_clients_windows': count_windows,
        'count_clients_office': count_office,
        'count_products': count_products,
        'count_products_filtered': noglvk,
        'count_products_windows': count_products_windows,
        'count_products_office': count_products_office,
        'count_projects': count_products,
        'db_path': _get_db_path(),
        'auth_db_path': auth.AUTH_DB_PATH if auth.is_enabled() else None,
        'version': version.get('hash'),
        'version_reference': version.get('reference'),
        'auth_enabled': auth.is_enabled(),
    }


def _current_user():
    uid = session.get('user_id')
    if not uid:
        return None
    return auth.get_user_by_id(uid)


@app.context_processor
def _inject_globals():
    user = _current_user()
    return {
        'auth_enabled': auth.is_enabled(),
        'current_user': user,
        'setup_required': auth.is_enabled() and not auth.is_setup_complete(),
    }


@app.before_request
def _guard_auth():
    if not auth.is_enabled():
        return None
    path = request.path
    if path.startswith('/static/'):
        return None
    if path in _PUBLIC_PATHS:
        return None
    if not auth.is_setup_complete():
        if path != '/setup':
            return redirect(url_for('setup_page'))
        return None
    if path == '/setup':
        return redirect(url_for('dashboard'))
    if 'user_id' not in session:
        if path == '/login':
            return None
        nxt = path if path != '/' else None
        return redirect(url_for('login_page', next=nxt))
    return None


# ── Auth routes ──

@app.route('/setup', methods=['GET', 'POST'])
def setup_page():
    if not auth.is_enabled():
        return redirect(url_for('dashboard'))
    if auth.is_setup_complete():
        return redirect(url_for('dashboard'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')
        if password != confirm:
            error = 'Passwords do not match'
        else:
            try:
                auth.create_admin(username, password)
                user = auth.verify_login(username, password)
                session.clear()
                session.permanent = True
                session['user_id'] = user['id']
                session['username'] = user['username']
                flash('Administrator account created successfully.', 'success')
                return redirect(url_for('dashboard'))
            except ValueError as e:
                error = str(e)
    return render_template('setup.html', path='/setup/', error=error)


@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if not auth.is_enabled():
        return redirect(url_for('dashboard'))
    if not auth.is_setup_complete():
        return redirect(url_for('setup_page'))
    error = None
    nxt = request.args.get('next') or request.form.get('next') or url_for('dashboard')
    if request.method == 'POST':
        user = auth.verify_login(
            request.form.get('username', ''),
            request.form.get('password', ''),
        )
        if user:
            session.clear()
            session.permanent = request.form.get('remember') == 'on'
            session['user_id'] = user['id']
            session['username'] = user['username']
            if not nxt.startswith('/') or nxt.startswith('//'):
                nxt = url_for('dashboard')
            return redirect(nxt)
        error = 'Invalid username or password'
    return render_template('login.html', path='/login/', error=error, next_url=nxt)


@app.route('/logout', methods=['POST'])
def logout_page():
    session.clear()
    if auth.is_enabled():
        flash('You have been signed out.', 'success')
        return redirect(url_for('login_page'))
    return redirect(url_for('dashboard'))


@app.route('/admin', methods=['GET', 'POST'])
def admin_page():
    _increase_serve_count()
    user = _current_user()
    profile = auth.get_admin_profile()
    stats = _build_stats()
    error = None
    success = None

    if request.method == 'POST' and request.form.get('action') == 'change_password':
        try:
            auth.change_password(
                user['id'],
                request.form.get('current_password', ''),
                request.form.get('new_password', ''),
            )
            success = 'Password updated successfully'
        except ValueError as e:
            error = str(e)

    if profile:
        profile['created_at_fmt'] = _format_ts(profile.get('created_at'))
        profile['last_login_fmt'] = _format_ts(profile.get('last_login'))

    return render_template(
        'admin.html',
        path='/admin/',
        profile=profile,
        stats=stats,
        error=error,
        success=success,
        min_password_len=auth.MIN_PASSWORD_LEN,
    )


# ── App routes ──

@app.route('/')
def dashboard():
    _increase_serve_count()
    error = None
    stats = None
    try:
        clients = _load_clients()
        stats = _build_stats(clients)
    except Exception as e:
        error = str(e)
        stats = _build_stats([])
    return render_template(
        'dashboard.html',
        path='/',
        error=error,
        stats=stats,
    ), 200 if error is None else 500


@app.route('/clients')
def clients_page():
    _increase_serve_count()
    error = None
    clients = None
    try:
        clients = _load_clients()
    except Exception as e:
        error = str(e)
    count_clients, count_windows, count_office = _client_counts(clients)
    _, _, count_products, _, _ = _product_counts()
    return render_template(
        'clients.html',
        path='/clients/',
        error=error,
        clients=clients,
        count_clients=count_clients,
        count_clients_windows=count_windows,
        count_clients_office=count_office,
        count_projects=count_products,
    ), 200 if error is None else 500


@app.route('/api/v1/stats')
def api_stats():
    _increase_serve_count()
    try:
        _env_check()
        clients = _load_clients()
        return jsonify(_build_stats(clients))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/clients')
def api_clients():
    _increase_serve_count()
    try:
        _env_check()
        return jsonify(_load_clients())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/clients/export')
def api_clients_export():
    _increase_serve_count()
    try:
        _env_check()
        clients = _load_clients()
        output = io.StringIO()
        if clients:
            fieldnames = list(clients[0].keys())
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(clients)
        else:
            output.write('clientMachineId,machineName,machineIp,applicationId,skuId,licenseStatus,lastRequestTime,kmsEpid,requestCount\n')
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=kms-clients.csv'},
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/readyz')
def readyz():
    try:
        _env_check()
    except Exception as e:
        return f'Whooops! {e}', 503
    if _uptime_seconds() > 10:
        return 'OK', 200
    return 'Not ready', 503


@app.route('/livez')
def livez():
    try:
        _env_check()
        return 'OK', 200
    except Exception as e:
        return f'Whooops! {e}', 503


@app.route('/license')
def license_page():
    _increase_serve_count()
    with open(os.environ.get('PYKMS_LICENSE_PATH', '../LICENSE'), 'r') as f:
        return render_template(
            'license.html',
            path='/license/',
            license=f.read()
        )


@app.route('/products')
def products():
    _increase_serve_count()
    items, noglvk, count_products, count_windows, count_office = _product_counts()
    return render_template(
        'products.html',
        path='/products/',
        products=items,
        filtered=noglvk,
        count_products=count_products,
        count_products_windows=count_windows,
        count_products_office=count_office,
    )
