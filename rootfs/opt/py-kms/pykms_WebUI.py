import csv
import io
import os
import uuid
import datetime

from flask import Flask, jsonify, render_template, Response
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


app = Flask('pykms_webui')
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


def _env_check():
    if _dbEnvVarName not in os.environ:
        raise Exception(f'Environment variable is not set: {_dbEnvVarName}')


def _get_db_path():
    return os.environ.get(_dbEnvVarName)


def _load_clients():
    db_path = _get_db_path()
    if not db_path:
        raise Exception(f'Environment variable is not set: {_dbEnvVarName}')
    return sql_get_all(db_path)


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
        'version': version.get('hash'),
        'version_reference': version.get('reference'),
    }


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
