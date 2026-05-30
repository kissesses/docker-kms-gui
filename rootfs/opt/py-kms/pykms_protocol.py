"""KMS client ↔ server protocol documentation and per-client session views."""

import pykms_activation as activation
from pykms_config import config

# Fields the client sends in each activation/renewal request (py-kms kmsRequest).
CLIENT_REQUEST_FIELDS = (
    {
        'key': 'clientMachineId',
        'label': 'Client Machine ID',
        'type': 'UUID',
        'direction': 'client',
        'description': 'Unique hardware/software identity of the activating machine.',
        'stored': True,
    },
    {
        'key': 'machineName',
        'label': 'Machine Name',
        'type': 'string',
        'direction': 'client',
        'description': 'NetBIOS / hostname reported by the client OS.',
        'stored': True,
    },
    {
        'key': 'applicationId',
        'label': 'Application ID',
        'type': 'UUID / name',
        'direction': 'client',
        'description': 'Product group — Windows, Office, etc.',
        'stored': True,
    },
    {
        'key': 'skuId',
        'label': 'SKU ID',
        'type': 'UUID / name',
        'direction': 'client',
        'description': 'Specific edition being activated (e.g. Windows 11 Pro).',
        'stored': True,
    },
    {
        'key': 'licenseStatus',
        'label': 'License Status',
        'type': 'enum',
        'direction': 'client',
        'description': 'Activated, Notifications Mode (grace), or other KMS state.',
        'stored': True,
    },
    {
        'key': 'requestTime',
        'label': 'Request Time',
        'type': 'FILETIME',
        'direction': 'client',
        'description': 'Client timestamp; server validates ±4h window.',
        'stored': False,
    },
    {
        'key': 'kmsCountedId',
        'label': 'KMS Counted ID',
        'type': 'binary',
        'direction': 'client',
        'description': 'Used to derive the server ePID for this product.',
        'stored': False,
    },
)

# Fields the KMS server returns in the binary response.
SERVER_RESPONSE_FIELDS = (
    {
        'key': 'kmsEpid',
        'label': 'KMS ePID',
        'type': 'string (UTF-16)',
        'direction': 'server',
        'description': 'Extended Product ID — binds this client to this KMS host.',
        'stored': True,
    },
    {
        'key': 'currentClientCount',
        'label': 'Current Client Count',
        'type': 'integer',
        'direction': 'server',
        'description': 'Reported activation count (policy client_count, min 26/5).',
        'stored': False,
    },
    {
        'key': 'vLActivationInterval',
        'label': 'Activation Interval',
        'type': 'minutes',
        'direction': 'server',
        'description': 'How often the client retries while in grace / notifications mode.',
        'stored': False,
    },
    {
        'key': 'vLRenewalInterval',
        'label': 'Renewal Interval',
        'type': 'minutes',
        'direction': 'server',
        'description': 'How often activated clients must re-contact KMS.',
        'stored': False,
    },
    {
        'key': 'clientMachineId',
        'label': 'Client Machine ID',
        'type': 'UUID',
        'direction': 'server',
        'description': 'Echoed back to confirm binding.',
        'stored': False,
    },
    {
        'key': 'responseTime',
        'label': 'Response Time',
        'type': 'FILETIME',
        'direction': 'server',
        'description': 'Server timestamp echoed from the request.',
        'stored': False,
    },
)

FLOW_STEPS = (
    {'id': 1, 'from': 'client', 'title': 'TCP connect', 'detail': 'Client opens TCP :1688 to KMS host (slmgr /skms).'},
    {'id': 2, 'from': 'client', 'title': 'KMS request', 'detail': 'Binary packet v4/v5/v6 with machine ID, SKU, license status.'},
    {'id': 3, 'from': 'server', 'title': 'Validate & log', 'detail': 'Server parses request, updates SQLite, logs activation.'},
    {'id': 4, 'from': 'server', 'title': 'KMS response', 'detail': 'Returns ePID, client count, activation & renewal intervals.'},
    {'id': 5, 'from': 'client', 'title': 'Apply license', 'detail': 'OS stores ePID and schedules next renewal per intervals.'},
)


def build_protocol_overview():
    policy = activation.load_policy()
    return {
        'transport': {
            'protocol': 'Microsoft KMS (Volume Activation)',
            'port': policy.get('port', config.KMS_PORT),
            'bind': f"0.0.0.0:{policy.get('port', config.KMS_PORT)}",
            'wire_format': 'Binary KMS v4 / v5 / v6 over TCP',
        },
        'policy': {
            'client_count': policy['client_count'],
            'activation_interval_minutes': policy['activation_interval_minutes'],
            'renewal_interval_minutes': policy['renewal_interval_minutes'],
            'activation_interval_fmt': activation.format_duration(policy['activation_interval_minutes']),
            'renewal_interval_fmt': activation.format_duration(policy['renewal_interval_minutes']),
            'licensing_validity_days': policy['licensing_validity_days'],
            'hwid': policy['hwid'],
        },
        'client_request_fields': list(CLIENT_REQUEST_FIELDS),
        'server_response_fields': list(SERVER_RESPONSE_FIELDS),
        'database_fields': [f for f in CLIENT_REQUEST_FIELDS if f['stored']] + [
            f for f in SERVER_RESPONSE_FIELDS if f['stored']
        ],
        'flow_steps': list(FLOW_STEPS),
        'thresholds': {
            'windows_min_clients': 25,
            'office_min_clients': 5,
        },
    }


def build_client_session(client, policy=None):
    """Human-readable last known exchange for one client row from the DB."""
    policy = policy or activation.load_policy()
    row = activation.enrich_client(client, policy)
    return {
        'binding': {
            'machine_name': row.get('machineName'),
            'client_machine_id': row.get('clientMachineId'),
            'application_id': row.get('applicationId'),
            'sku_id': row.get('skuId'),
            'kms_epid': row.get('kmsEpid'),
            'target': row.get('binding_target'),
        },
        'received_from_client': {
            'machineName': row.get('machineName'),
            'clientMachineId': row.get('clientMachineId'),
            'applicationId': row.get('applicationId'),
            'skuId': row.get('skuId'),
            'licenseStatus': row.get('licenseStatus'),
            'lastRequestIP': row.get('machineIp') or row.get('lastRequestIP'),
            'lastRequestTime': row.get('lastRequestTime'),
            'requestCount': row.get('requestCount'),
        },
        'sent_to_client': {
            'kmsEpid': row.get('kmsEpid') or '(generated on last response)',
            'currentClientCount': policy['client_count'],
            'vLActivationInterval': policy['activation_interval_minutes'],
            'vLRenewalInterval': policy['renewal_interval_minutes'],
            'clientMachineId': row.get('clientMachineId'),
        },
        'schedule': {
            'health': row.get('health'),
            'health_note': row.get('health_note'),
            'last_seen_fmt': row.get('last_seen_fmt'),
            'next_renewal_fmt': row.get('next_renewal_fmt'),
            'next_activation_fmt': row.get('next_activation_fmt'),
            'license_horizon_fmt': row.get('license_horizon_fmt'),
        },
    }


def find_client(clients, client_machine_id, application_id):
    for client in clients or []:
        if (
            client.get('clientMachineId') == client_machine_id
            and client.get('applicationId') == application_id
        ):
            return client
    return None
