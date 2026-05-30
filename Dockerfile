# Multi-image build — ghcr.io/kissesses/kms and kms-gui
#
#   docker build --target kms  -t ghcr.io/kissesses/kms:local .
#   docker build --target gui  -t ghcr.io/kissesses/kms-gui:local .

ARG PYKMS_REPO=https://github.com/Py-KMS-Organization/py-kms.git
ARG PYKMS_COMMIT=b0e1615dec06
ARG NGINX_VERSION=1.30.2
ARG BUILD_VERSION=dev
ARG APP_UID=1000
ARG APP_GID=1000

# ── Shared py-kms source ───────────────────────────────────────────────────
FROM alpine:3.22 AS pykms-src
ARG PYKMS_REPO
ARG PYKMS_COMMIT
RUN apk add --no-cache git \
  && git clone --filter=blob:none "${PYKMS_REPO}" /src \
  && cd /src && git checkout "${PYKMS_COMMIT}"

# ── KMS server (port 1688) ───────────────────────────────────────────────────
FROM alpine:3.22 AS kms

ARG BUILD_VERSION
ARG APP_UID
ARG APP_GID
ARG PYKMS_COMMIT

ENV IP=0.0.0.0 \
    PORT=1688 \
    LCID=1033 \
    CLIENT_COUNT=26 \
    ACTIVATION_INTERVAL=120 \
    RENEWAL_INTERVAL=10080 \
    HWID=RANDOM \
    LOGLEVEL=INFO \
    LOGFILE=STDOUT \
    TZ=UTC \
    KMS_DB_PATH=/kms/var/kms.db

RUN apk add --no-cache \
      bash python3 py3-pip sqlite-libs ca-certificates tzdata curl \
    && pip3 install --break-system-packages --no-cache-dir \
      dnspython==2.8.0 tzlocal==5.3.1

COPY --from=pykms-src /src/py-kms /opt/py-kms
COPY --from=pykms-src /src/LICENSE /LICENSE
COPY docker/kms/entrypoint.sh /usr/local/bin/entrypoint.sh

RUN echo "${BUILD_VERSION}" > /VERSION \
    && echo "${PYKMS_COMMIT}" >> /VERSION \
    && chmod +x /usr/local/bin/entrypoint.sh \
    && addgroup -g "${APP_GID}" kms 2>/dev/null || true \
    && adduser -S -u "${APP_UID}" -G kms kms 2>/dev/null || adduser -S -u "${APP_UID}" kms \
    && mkdir -p /kms/var \
    && chown -R "${APP_UID}:${APP_GID}" /kms/var /opt/py-kms

WORKDIR /opt/py-kms
VOLUME ["/kms/var"]
EXPOSE 1688/tcp
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD pgrep -f pykms_Server.py >/dev/null || exit 1

USER ${APP_UID}:${APP_GID}
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# ── Web GUI (nginx + gunicorn/Flask) ─────────────────────────────────────────
FROM nginx:${NGINX_VERSION}-alpine AS nginx

FROM alpine:3.22 AS gui

ARG NGINX_VERSION
ARG BUILD_VERSION
ARG APP_UID
ARG APP_GID
ARG PYKMS_COMMIT

ENV APP_ROOT=/kms \
    APP_UID=${APP_UID} \
    APP_GID=${APP_GID} \
    APP_VERSION=${BUILD_VERSION} \
    PYKMS_SQLITE_DB_PATH=/kms/var/kms.db \
    PYKMS_LICENSE_PATH=/opt/py-kms/LICENSE \
    PYKMS_VERSION_PATH=/opt/py-kms/VERSION \
    NGINX_VERSION=${NGINX_VERSION} \
    NGINX_ENABLED=true \
    NGINX_PORT=80 \
    GUNICORN_BIND=127.0.0.1:8080 \
    NGINX_TLS_ENABLED=false \
    NGINX_TLS_CERT=/etc/nginx/certs/cert.pem \
    NGINX_TLS_KEY=/etc/nginx/certs/key.pem \
    LOG_LEVEL=INFO \
    GUI_AUTH_ENABLED=false \
    ADMIN_PUBLIC=false \
    GUI_AUTH_DB_PATH=/kms/var/gui_auth.db \
    GUI_AUDIT_DB_PATH=/kms/var/gui_audit.db \
    GUI_SECRET_FILE=/kms/var/.gui_secret \
    KMS_POLICY_FILE=/kms/var/kms-policy.json

RUN apk add --no-cache \
      bash python3 py3-pip sqlite-libs ca-certificates tzdata curl \
      pcre2 zlib openssl apache2-utils \
    && pip3 install --break-system-packages --no-cache-dir \
      dnspython==2.8.0 tzlocal==5.3.1 Flask==3.1.2 gunicorn==23.0.0

COPY --from=pykms-src /src/py-kms /opt/py-kms
COPY --from=pykms-src /src/LICENSE /opt/py-kms/LICENSE
COPY --from=nginx /usr/sbin/nginx /usr/sbin/nginx
COPY --from=nginx /etc/nginx/mime.types /etc/nginx/mime.types
COPY --from=nginx /etc/nginx/fastcgi_params /etc/nginx/fastcgi_params
COPY --from=nginx /etc/nginx/scgi_params /etc/nginx/scgi_params
COPY --from=nginx /etc/nginx/uwsgi_params /etc/nginx/uwsgi_params
COPY --from=nginx /usr/lib/nginx /usr/lib/nginx

RUN nginx -v 2>&1 | grep -q "${NGINX_VERSION}" \
    && mkdir -p /var/log/nginx /var/cache/nginx /run/nginx /etc/nginx/certs

COPY rootfs/ /

RUN set -ex \
    && echo "${BUILD_VERSION}" > /opt/py-kms/VERSION \
    && echo "${PYKMS_COMMIT}" >> /opt/py-kms/VERSION \
    && mkdir -p ${APP_ROOT}/var ${APP_ROOT}/styles/custom-icon \
    && rm -rf /opt/py-kms/templates /opt/py-kms/static \
    && addgroup -g "${APP_GID}" kms 2>/dev/null || true \
    && adduser -S -u "${APP_UID}" -G kms kms 2>/dev/null || adduser -S -u "${APP_UID}" kms \
    && chmod +x /usr/local/bin/*.sh \
    && chown -R ${APP_UID}:${APP_GID} ${APP_ROOT} /opt/py-kms /var/log/nginx /var/cache/nginx /run/nginx

VOLUME ["/kms/var"]
EXPOSE 80 443
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
  CMD /usr/local/bin/healthcheck.sh

USER root
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
