#!/bin/ash
set -e

GUNICORN_PID=""
NGINX_PID=""

_log() {
  echo "[kms-gui] $(date '+%Y-%m-%d %H:%M:%S') $*"
}

_shutdown() {
  if [ -n "${NGINX_PID}" ]; then
    kill -TERM "${NGINX_PID}" 2>/dev/null || true
  fi
  if [ -n "${GUNICORN_PID}" ]; then
    kill -TERM "${GUNICORN_PID}" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
}

trap _shutdown TERM INT

_configure_auth() {
  if [ -n "${NGINX_BASIC_AUTH_USER}" ] && [ -n "${NGINX_BASIC_AUTH_PASS}" ]; then
    htpasswd -bc /etc/nginx/.htpasswd "${NGINX_BASIC_AUTH_USER}" "${NGINX_BASIC_AUTH_PASS}"
    cat > /etc/nginx/conf.d/auth.conf <<'EOF'
auth_basic "KMS GUI";
auth_basic_user_file /etc/nginx/.htpasswd;
EOF
    _log "nginx basic auth enabled"
  else
    echo "# no auth" > /etc/nginx/conf.d/auth.conf
  fi
}

_validate_security() {
  if [ "${INTERNET_MODE}" = "true" ]; then
    if [ "${GUI_AUTH_ENABLED}" != "true" ]; then
      _log "ERROR: INTERNET_MODE requires GUI_AUTH_ENABLED=true"
      exit 1
    fi
    if [ "${DEBUG}" != "" ]; then
      _log "ERROR: DEBUG must not be enabled in INTERNET_MODE"
      exit 1
    fi
    _log "internet mode: application auth required"
  fi
  if [ "${GUI_AUTH_ENABLED}" = "true" ]; then
    _log "application auth enabled (setup at /setup on first run)"
  elif [ -n "${NGINX_BASIC_AUTH_PASS}" ] && [ ${#NGINX_BASIC_AUTH_PASS} -lt 12 ]; then
    _log "WARNING: NGINX_BASIC_AUTH_PASS is shorter than 12 characters — use a longer password"
  fi
  if [ "${NGINX_ENABLED}" = "true" ] && [ "${GUI_AUTH_ENABLED}" != "true" ]; then
    if [ -z "${NGINX_BASIC_AUTH_USER}" ] || [ -z "${NGINX_BASIC_AUTH_PASS}" ]; then
      _log "WARNING: Web UI has no authentication — enable GUI_AUTH_ENABLED or NGINX_BASIC_AUTH"
    fi
  fi
}

_configure_tls() {
  if [ "${NGINX_TLS_ENABLED}" = "true" ]; then
    if [ ! -f "${NGINX_TLS_CERT}" ] || [ ! -f "${NGINX_TLS_KEY}" ]; then
      _log "ERROR: TLS enabled but cert/key not found"
      exit 1
    fi
    cat > /etc/nginx/conf.d/tls.conf <<EOF
server {
    listen 443 ssl;
    server_name _;
    ssl_certificate ${NGINX_TLS_CERT};
    ssl_certificate_key ${NGINX_TLS_KEY};
    ssl_protocols TLSv1.2 TLSv1.3;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    include /etc/nginx/conf.d/auth.conf;
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options SAMEORIGIN always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'self';" always;
    location /api/ {
        limit_req zone=api_limit burst=10 nodelay;
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    location ~ ^/(login|setup)$ {
        limit_req zone=auth_limit burst=3 nodelay;
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    location / {
        limit_req zone=general_limit burst=30 nodelay;
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
    _log "nginx TLS enabled on port 443"
  else
    rm -f /etc/nginx/conf.d/tls.conf
  fi
}

if [ -z "${1}" ]; then

  if [ -n "${DEBUG}" ]; then
    LOG_LEVEL="DEBUG"
    _log "debug mode enabled"
  fi

  mkdir -p "${APP_ROOT}/var"
  chown -R "${APP_UID:-1000}:${APP_GID:-1000}" "${APP_ROOT}/var"

  rm -rf /opt/py-kms/templates /opt/py-kms/static
  ln -sf "${APP_ROOT}/styles/custom-icon/templates" /opt/py-kms/templates
  ln -sf "${APP_ROOT}/styles/custom-icon/static" /opt/py-kms/static
  _log "UI theme: custom-icon"

  cd /opt/py-kms

  if [ "${NGINX_ENABLED}" = "true" ]; then
    GUNICORN_BIND_ADDR="${GUNICORN_BIND:-127.0.0.1:8080}"
  else
    GUNICORN_BIND_ADDR="${GUNICORN_BIND:-0.0.0.0:8080}"
    _log "nginx disabled, gunicorn on ${GUNICORN_BIND_ADDR}"
  fi

  gunicorn \
    --log-level "${LOG_LEVEL}" \
    --bind "${GUNICORN_BIND_ADDR}" \
    --user "${APP_UID:-1000}" \
    --group kms \
    pykms_WebUI:app &
  GUNICORN_PID=$!

  if [ "${NGINX_ENABLED}" = "true" ]; then
    _validate_security
    _configure_auth
    _configure_tls
    nginx -t
    nginx -g 'daemon off;' &
    NGINX_PID=$!
    _log "nginx ${NGINX_VERSION} listening on port ${NGINX_PORT}"
  fi

  _log "started (version ${APP_VERSION})"

  while kill -0 "${GUNICORN_PID}" 2>/dev/null; do
    if [ -n "${NGINX_PID}" ] && ! kill -0 "${NGINX_PID}" 2>/dev/null; then
      break
    fi
    sleep 1
  done

  _shutdown
  exit 1
fi

exec "$@"
