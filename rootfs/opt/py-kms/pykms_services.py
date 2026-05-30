"""Business logic: clients, stats, products."""

import datetime
import os
import sqlite3

from pykms_DB2Dict import kmsDB2Dict
from pykms_Sql import sql_get_all

import pykms_auth as auth
from pykms_config import config

_kms_items = None
_kms_items_noglvk = None
_start_time = datetime.datetime.now()


def start_time():
    return _start_time


def uptime_seconds():
    return int((datetime.datetime.now() - _start_time).total_seconds())


def parse_ts(ts):
    """Unix epoch from int, numeric string, or ISO datetime (py-kms variants)."""
    if ts is None or ts == '':
        return None
    if isinstance(ts, bool):
        return None
    if isinstance(ts, (int, float)):
        return int(ts)
    if isinstance(ts, str):
        s = ts.strip()
        if not s:
            return None
        if s.isdigit():
            return int(s)
        try:
            return int(float(s))
        except ValueError:
            pass
        iso = s[:-1] + '+00:00' if s.endswith('Z') else s
        try:
            return int(datetime.datetime.fromisoformat(iso).timestamp())
        except ValueError:
            pass
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
            try:
                return int(datetime.datetime.strptime(s, fmt).timestamp())
            except ValueError:
                continue
    return None


def format_ts(ts):
    parsed = parse_ts(ts)
    if parsed is None:
        return 'Never'
    return datetime.datetime.fromtimestamp(parsed).strftime('%Y-%m-%d %H:%M:%S')


def env_check():
    if not config.DB_PATH:
        raise RuntimeError('PYKMS_SQLITE_DB_PATH is not set')


def load_clients():
    env_check()
    import time
    last_err = None
    for attempt in range(5):
        try:
            clients = sql_get_all(config.DB_PATH)
            if clients:
                for client in clients:
                    if 'machineIp' not in client and 'lastRequestIP' in client:
                        client['machineIp'] = client['lastRequestIP']
            return clients
        except sqlite3.OperationalError as e:
            last_err = e
            if 'locked' not in str(e).lower():
                raise
            time.sleep(0.2 * (attempt + 1))
    raise last_err


def delete_client(client_machine_id, application_id):
    env_check()
    with sqlite3.connect(config.DB_PATH, timeout=10) as con:
        cur = con.execute(
            'DELETE FROM clients WHERE clientMachineId = ? AND applicationId = ?',
            (client_machine_id, application_id),
        )
        return cur.rowcount > 0


def client_counts(clients):
    if not clients:
        return 0, 0, 0
    total = len(clients)
    windows = len([c for c in clients if c.get('applicationId') == 'Windows'])
    return total, windows, total - windows


def _get_kms_items_cache():
    global _kms_items, _kms_items_noglvk
    if _kms_items is None:
        _kms_items = {}
        _kms_items_noglvk = 0
        for section in kmsDB2Dict():
            for element in section:
                if 'KmsItems' in element:
                    for product in element['KmsItems']:
                        group_name = product['DisplayName']
                        items = {}
                        for item in product['SkuItems']:
                            items[item['DisplayName']] = item['Gvlk']
                            if not item['Gvlk']:
                                _kms_items_noglvk += 1
                        if items:
                            if group_name not in _kms_items:
                                _kms_items[group_name] = {}
                            _kms_items[group_name].update(items)
    return _kms_items, _kms_items_noglvk


def product_counts():
    items, noglvk = _get_kms_items_cache()
    count_products = sum(len(entries) for entries in items.values())
    count_windows = sum(
        len(entries) for name, entries in items.items() if 'windows' in name.lower()
    )
    count_office = sum(
        len(entries) for name, entries in items.items() if 'office' in name.lower()
    )
    return items, noglvk, count_products, count_windows, count_office


def load_version_info():
    if not os.path.exists(config.VERSION_PATH):
        return None
    with open(config.VERSION_PATH, 'r', encoding='utf-8') as f:
        return {'hash': f.readline().strip(), 'reference': f.readline().strip()}


def build_stats(clients=None):
    if clients is None:
        try:
            clients = load_clients()
        except Exception:
            clients = None
    count_clients, count_windows, count_office = client_counts(clients)
    _, noglvk, count_products, cpw, cpo = product_counts()
    version = load_version_info() or {}
    return {
        'uptime_seconds': uptime_seconds(),
        'count_clients': count_clients,
        'count_clients_windows': count_windows,
        'count_clients_office': count_office,
        'count_products': count_products,
        'count_products_filtered': noglvk,
        'count_products_windows': cpw,
        'count_products_office': cpo,
        'count_projects': count_products,
        'db_path': config.DB_PATH,
        'auth_db_path': auth.AUTH_DB_PATH if auth.is_enabled() else None,
        'version': version.get('hash'),
        'version_reference': version.get('reference'),
        'auth_enabled': auth.is_enabled(),
        'chart_windows': count_windows,
        'chart_office': count_office,
    }
