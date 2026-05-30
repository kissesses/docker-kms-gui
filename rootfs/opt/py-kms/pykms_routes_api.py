"""REST API routes."""

import csv
import io

from flask import Blueprint, Response, jsonify

import pykms_activation as activation
import pykms_audit as audit
import pykms_csrf as csrf
from pykms_services import build_stats, env_check, load_clients, uptime_seconds

api_bp = Blueprint('api', __name__)


@api_bp.route('/api/v1/stats')
def api_stats():
    try:
        env_check()
        clients = load_clients()
        return jsonify(build_stats(clients))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/v1/clients')
def api_clients():
    try:
        env_check()
        return jsonify(load_clients())
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
