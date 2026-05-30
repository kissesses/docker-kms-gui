# Security guide

Personal deployment checklist for **kissesses/docker-kms-gui**.

## Threat model

This stack is designed for **home / lab use**:

- KMS activation server (port 1688)
- Web dashboard with client data and REST API
- Shared SQLite database between containers

**Do not expose the Web GUI to the public internet without hardening.**

---

## Current security measures

| Layer | Protection |
|-------|------------|
| nginx 1.30.2 | CVE-2026-9256 patched; no risky rewrite rules |
| Reverse proxy | Gunicorn on `127.0.0.1:8080` only (default mode) |
| Headers | CSP, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy |
| Rate limits | 10 req/s on `/`, 30 req/s on `/api/`; **5 req/min** on `/login` and `/setup` |
| CSRF | Flask session tokens on all POST forms |
| Auth | Application login (`GUI_AUTH_ENABLED`) or nginx Basic Auth |
| Admin guard | `/admin*` hidden when auth off unless `ADMIN_PUBLIC=true` |
| TLS | Optional; HSTS when TLS enabled |
| Build | py-kms pinned to specific commit (supply chain) |
| CI | Grype scan (HIGH/CRITICAL, fixed only), SARIF reports, Dependabot updates |

---

## Deployment profiles

| Profile | Compose file | Use case |
|---------|--------------|----------|
| **Local** (default) | `compose.yaml` | `127.0.0.1` only |
| **Internet** | `compose.internet.yaml` | KMS public, GUI localhost + TLS + auth |
| **Sidecar** | `compose.sidecar.yaml` | External nginx; add auth via `sidecar-auth.conf.example` |

---

## Local / home (recommended)

```env
BIND_ADDRESS=127.0.0.1
NGINX_BASIC_AUTH_USER=admin
NGINX_BASIC_AUTH_PASS=long-random-password-here
```

```bash
cp .env.example .env
docker compose up -d
```

---

## Internet deployment

KMS and GUI can both be public when **application auth** is enabled:

```bash
cp .env.internet.example .env
# Place cert.pem + key.pem in ./certs/
docker compose -f compose.internet.yaml up -d
```

First visit: **`https://your-server/setup`** — create administrator account.

| Setting | Value | Why |
|---------|-------|-----|
| `KMS_BIND` | `0.0.0.0` | Windows clients connect from internet |
| `GUI_BIND` | `0.0.0.0` | Web panel accessible over HTTPS |
| `GUI_AUTH_ENABLED` | `true` | Required — enforced by `INTERNET_MODE=true` |
| `NGINX_TLS_ENABLED` | `true` | HTTPS for login and sessions |
| `DEBUG` | empty | Blocked in internet mode |

After setup, sign in at `/login`. Manage account at `/admin`.

Set `ADMIN_PUBLIC=false` (default) so admin routes stay hidden when auth is disabled on LAN deployments.

---

## Application auth (local or internet)

```env
GUI_AUTH_ENABLED=true
```

1. Open **`/setup`** — create admin (once, min 12 char password)
2. Sign in at **`/login`**
3. Change password at **`/admin`**

When `GUI_AUTH_ENABLED=true`, nginx Basic Auth is optional (double auth is possible but not required).

---

## Split bind (LAN)

```env
KMS_BIND=0.0.0.0      # KMS for LAN clients
GUI_BIND=127.0.0.1    # GUI local only
```

---

## Sidecar auth

```bash
cp nginx/sidecar-auth.conf.example nginx/sidecar-auth.conf
htpasswd -cb nginx/.htpasswd admin your-strong-password
```

Mount in `compose.sidecar.yaml` (see example file comments).

---

## Known limitations

| Risk | Severity | Mitigation |
|------|----------|------------|
| GUI container runs nginx as root | Low (local) | Bind GUI to localhost |
| API has no separate auth token | Medium | Enable `GUI_AUTH_ENABLED`; CSRF on writes |
| KMS protocol unencrypted on 1688 | Medium | Expected for KMS; limit exposure |
| Password in env vars | Low | Docker secrets for production |
| py-kms upstream trust | Low | Commit pinned in Dockerfile |

---

## Reporting issues

Open an issue: https://github.com/kissesses/docker-kms-gui/issues

For py-kms engine vulnerabilities: https://github.com/Py-KMS-Organization/py-kms
