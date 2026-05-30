"""REST API routes."""

import csv
import io

from flask import Blueprint, Response, jsonify, request

import pykms_activation as activation
import pykms_audit as audit
import pykms_auth as auth
from pykms_routes_auth import current_user
from pykms_config import config
from pykms_services import build_stats, env_check, filter_clients, flatten_product_keys, load_clients, uptime_seconds

api_bp = Blueprint('api', __name__)


@api_bp.before_request
def require_api_auth():
    if request.path in ('/livez', '/readyz'):
        return None
    if request.path == '/api/v1/keys/public':
        return None
    if not request.path.startswith('/api/'):
        return None
    if not auth.api_protection_enabled():
        return None
    if auth.verify_api_bearer() or current_user():
        return None
    return jsonify({'error': 'Unauthorized'}), 401


@api_bp.route('/api/v1/keys/public')
def api_keys_public():
    if not config.KEYS_PUBLIC:
        return jsonify({'error': 'Forbidden'}), 403
    try:
        keys, _ = flatten_product_keys()
        return jsonify([
            {
                'category': row['category'],
                'name': row['name'],
                'gvlk': row['gvlk'],
                'type': row['type'],
            }
            for row in keys
            if row['gvlk']
        ])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/v1/stats')
def api_stats():
    try:
        env_check()
        clients = load_clients()
        return jsonify(build_stats(clients, include_products=False))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/v1/clients')
def api_clients():
    try:
        env_check()
        clients = load_clients()
        clients = filter_clients(
            clients,
            query=request.args.get('q'),
            application=request.args.get('app'),
            status=request.args.get('status'),
            health=request.args.get('health'),
        )
        return jsonify(clients)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/v1/clients/export')
def api_clients_export():
    try:
        env_check()
        clients = load_clients()
        audit.log('export_csv')
        output = io.StringIO()
        if clients:
            fieldnames = list(clients[0].keys())
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(clients)
        else:
            output.write(
                'clientMachineId,machineName,machineIp,applicationId,skuId,'
                'licenseStatus,lastRequestTime,kmsEpid,requestCount\n'
            )
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=kms-clients.csv'},
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/v1/activations')
def api_activations():
    try:
        env_check()
        clients = load_clients()
        return jsonify(activation.build_activation_overview(clients))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/v1/protocol')
def api_protocol():
    import pykms_protocol as protocol
    try:
        env_check()
        return jsonify(protocol.build_protocol_overview())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/v1/diagnostics')
def api_diagnostics():
    import pykms_diagnostics as diagnostics
    try:
        env_check()
        return jsonify(diagnostics.build_report())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/v1/clients/<client_id>/<application_id>/session')
def api_client_session(client_id, application_id):
    import pykms_protocol as protocol
    try:
        env_check()
        clients = load_clients()
        client = protocol.find_client(clients, client_id, application_id)
        if not client:
            return jsonify({'error': 'Not found'}), 404
        return jsonify(protocol.build_client_session(client))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/v1/clients/<client_id>/<application_id>', methods=['DELETE'])
def api_delete_client(client_id, application_id):
    from pykms_services import delete_client as svc_delete
    try:
        env_check()
        if svc_delete(client_id, application_id):
            audit.log('client_delete', client_id)
            return jsonify({'ok': True})
        return jsonify({'error': 'Not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/readyz')
def readyz():
    try:
        env_check()
    except Exception as e:
        return f'Whooops! {e}', 503
    if uptime_seconds() > 10:
        return 'OK', 200
    return 'Not ready', 503


@api_bp.route('/livez')
def livez():
    try:
        env_check()
        return 'OK', 200
    except Exception as e:
        return f'Whooops! {e}', 503
