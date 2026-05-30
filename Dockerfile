# KMS Web GUI — maintained by kissesses
# Standalone build on py-kms + nginx 1.30.2

ARG NGINX_VERSION=1.30.2
ARG PYKMS_REPO=https://github.com/Py-KMS-Organization/py-kms.git
ARG PYKMS_COMMIT=b0e1615dec06
ARG BUILD_VERSION=dev
ARG APP_UID=1000
ARG APP_GID=1000

FROM nginx:${NGINX_VERSION}-alpine AS nginx

FROM alpine:3.22 AS pykms-src
  ARG PYKMS_REPO
  ARG PYKMS_COMMIT
  RUN apk add --no-cache git \
    && git clone --filter=blob:none "${PYKMS_REPO}" /src \
    && cd /src && git checkout "${PYKMS_COMMIT}"

FROM alpine:3.22

  ARG NGINX_VERSION
  ARG BUILD_VERSION
  ARG APP_UID
  ARG APP_GID
  ARG PYKMS_COMMIT=b0e1615dec06

  ENV APP_ROOT=/kms
  ENV APP_UID=${APP_UID}
  ENV APP_GID=${APP_GID}
  ENV APP_VERSION=${BUILD_VERSION}

  ENV PYKMS_SQLITE_DB_PATH=/kms/var/kms.db
  ENV PYKMS_LICENSE_PATH=/opt/py-kms/LICENSE
  ENV PYKMS_VERSION_PATH=/opt/py-kms/VERSION

  ENV NGINX_VERSION=${NGINX_VERSION}
  ENV NGINX_ENABLED=true
  ENV NGINX_PORT=80
  ENV GUNICORN_BIND=127.0.0.1:8080
  ENV NGINX_TLS_ENABLED=false
  ENV NGINX_TLS_CERT=/etc/nginx/certs/cert.pem
  ENV NGINX_TLS_KEY=/etc/nginx/certs/key.pem
  ENV LOG_LEVEL=INFO

  ENV GUI_AUTH_ENABLED=false
  ENV ADMIN_PUBLIC=false
  ENV GUI_AUTH_DB_PATH=/kms/var/gui_auth.db
  ENV GUI_AUDIT_DB_PATH=/kms/var/gui_audit.db
  ENV GUI_SECRET_FILE=/kms/var/.gui_secret

  ENV KMS_POLICY_FILE=/kms/var/kms-policy.json
  ENV KMS_CLIENT_COUNT=26
  ENV KMS_ACTIVATION_INTERVAL=120
  ENV KMS_RENEWAL_INTERVAL=10080
  ENV KMS_HWID=RANDOM
  ENV KMS_PORT=1688

  RUN apk add --no-cache \
      bash \
      python3 \
      py3-pip \
      sqlite-libs \
      ca-certificates \
      tzdata \
      curl \
      pcre2 \
      zlib \
      openssl \
      apache2-utils \
    && pip3 install --break-system-packages --no-cache-dir \
      dnspython==2.8.0 \
      tzlocal==5.3.1 \
      Flask==3.1.2 \
      gunicorn==23.0.0

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
