#!/bin/ash
set -e

DB_DIR=$(dirname "${KMS_DB_PATH}")
mkdir -p "${DB_DIR}"

echo "[kms] starting on ${IP}:${PORT}, db=${KMS_DB_PATH}"
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
