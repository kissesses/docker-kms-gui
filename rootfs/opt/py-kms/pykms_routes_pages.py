"""Main UI pages."""

import time

from flask import Blueprint, render_template

import pykms_activation as activation
from pykms_services import build_stats, client_counts, load_clients, product_counts

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/')
def dashboard():
    error = None
    stats = None
    try:
        clients = load_clients()
        stats = build_stats(clients)
    except Exception as e:
        error = str(e)
        stats = build_stats([])
    return render_template(
        'dashboard.html', path='/', error=error, stats=stats,
    ), 200 if error is None else 500


@pages_bp.route('/clients')
def clients_page():
    error = None
    clients = []
    raw = []
    try:
        raw = load_clients()
        policy = activation.load_policy()
        now = int(time.time())
        clients = [activation.enrich_client(c, policy, now) for c in raw]
    except Exception as e:
        error = str(e)
    count_clients, count_windows, count_office = client_counts(raw if not error else [])
    _, _, count_products, _, _ = product_counts()
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


@pages_bp.route('/products')
def products():
    items, noglvk, count_products, count_windows, count_office = product_counts()
    return render_template(
        'products.html',
        path='/products/',
        products=items,
        filtered=noglvk,
        count_products=count_products,
        count_products_windows=count_windows,
        count_products_office=count_office,
    )


@pages_bp.route('/license')
def license_page():
    import os
    from pykms_config import config
    with open(config.LICENSE_PATH, 'r', encoding='utf-8') as f:
        return render_template('license.html', path='/license/', license=f.read())
