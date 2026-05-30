#!/bin/ash
set -e

DB_DIR=$(dirname "${KMS_DB_PATH}")
mkdir -p "${DB_DIR}"

POLICY_FILE="${KMS_DB_PATH%/*}/kms-policy.json"

_load_policy() {
  if [ ! -f "${POLICY_FILE}" ]; then
    return 1
  fi
  python3 - "${POLICY_FILE}" <<'PY'
import json
import sys

path = sys.argv[1]
try:
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
except (OSError, json.JSONDecodeError):
    sys.exit(1)

def emit(name, value):
    print(f'{name}={value}')

emit('CLIENT_COUNT', int(data.get('client_count', 26)))
emit('ACTIVATION_INTERVAL', int(data.get('activation_interval_minutes', 120)))
emit('RENEWAL_INTERVAL', int(data.get('renewal_interval_minutes', 10080)))
emit('HWID', str(data.get('hwid', 'RANDOM')))
if data.get('port') is not None:
    emit('PORT', int(data.get('port', 1688)))
PY
}

if _load_policy > /tmp/kms-policy.env 2>/dev/null; then
  # shellcheck disable=SC1091
  . /tmp/kms-policy.env
  rm -f /tmp/kms-policy.env
  echo "[kms] loaded policy from ${POLICY_FILE}"
else
  cat > "${POLICY_FILE}" <<EOF
{
  "client_count": ${CLIENT_COUNT},
  "activation_interval_minutes": ${ACTIVATION_INTERVAL},
  "renewal_interval_minutes": ${RENEWAL_INTERVAL},
  "hwid": "${HWID}",
  "port": ${PORT},
  "host": "kms",
  "licensing_validity_days": 180,
  "updated_at": $(date +%s),
  "pending_kms_restart": false
}
EOF
  echo "[kms] created default policy at ${POLICY_FILE}"
fi

echo "[kms] starting on ${IP}:${PORT}, db=${KMS_DB_PATH}, clients=${CLIENT_COUNT}"

cd /opt/py-kms

set -- python3 -u pykms_Server.py "${IP}" "${PORT}" \
  -l "${LCID}" \
  -c "${CLIENT_COUNT}" \
  -a "${ACTIVATION_INTERVAL}" \
  -r "${RENEWAL_INTERVAL}" \
  -w "${HWID}" \
  -V "${LOGLEVEL}" \
  -s "${KMS_DB_PATH}"

if [ "${LOGFILE}" != "STDOUT" ] && [ -n "${LOGFILE}" ]; then
  set -- "$@" -F "${LOGFILE}"
fi

if [ -n "${EPID}" ]; then
  set -- "$@" -e "${EPID}"
fi

exec "$@"
