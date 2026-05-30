#!/bin/ash
set -e

if [ "${NGINX_ENABLED}" = "true" ]; then
  curl -fsS "http://127.0.0.1:${NGINX_PORT:-80}/livez" > /dev/null
else
  curl -fsS "http://127.0.0.1:8080/livez" > /dev/null
fi
