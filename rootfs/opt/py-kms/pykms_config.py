"""Central configuration from environment variables."""

import os


def _flag(name, default=False):
    return os.environ.get(name, 'true' if default else 'false').lower() in ('1', 'true', 'yes')


def _int(name, default):
    raw = os.environ.get(name)
    if raw is None or raw == '':
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class Config:
    DB_PATH = os.environ.get('PYKMS_SQLITE_DB_PATH', '/kms/var/kms.db')
    LICENSE_PATH = os.environ.get('PYKMS_LICENSE_PATH', '/opt/py-kms/LICENSE')
    VERSION_PATH = os.environ.get('PYKMS_VERSION_PATH', '/opt/py-kms/VERSION')
    SECRET_FILE = os.environ.get('GUI_SECRET_FILE', '/kms/var/.gui_secret')
    POLICY_FILE = os.environ.get('KMS_POLICY_FILE', '/kms/var/kms-policy.json')
    AUDIT_DB = os.environ.get('GUI_AUDIT_DB_PATH', '/kms/var/gui_audit.db')

    GUI_AUTH_ENABLED = _flag('GUI_AUTH_ENABLED')
    ADMIN_PUBLIC = _flag('ADMIN_PUBLIC')
    KEYS_PUBLIC = _flag('KEYS_PUBLIC', default=True)

    KMS_CLIENT_COUNT = _int('KMS_CLIENT_COUNT', _int('CLIENT_COUNT', 26))
    KMS_ACTIVATION_INTERVAL = _int('KMS_ACTIVATION_INTERVAL', _int('ACTIVATION_INTERVAL', 120))
    KMS_RENEWAL_INTERVAL = _int('KMS_RENEWAL_INTERVAL', _int('RENEWAL_INTERVAL', 10080))
    KMS_HWID = os.environ.get('KMS_HWID', os.environ.get('HWID', 'RANDOM'))
    KMS_PORT = _int('KMS_PORT', _int('PORT', 1688))

    TLS_ENABLED = _flag('NGINX_TLS_ENABLED')
    DEFAULT_LANG = os.environ.get('GUI_DEFAULT_LANG', 'en')


config = Config()
