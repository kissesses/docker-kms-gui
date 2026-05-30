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
| Rate limits | 10 req/s on `/`, 30 req/s on `/api/` |
| TLS | Optional; HSTS when TLS enabled |
| Auth | Optional HTTP Basic Auth via nginx |
| Build | py-kms pinned to specific commit (supply chain) |
| CI | Trivy scan (CRITICAL/HIGH), Dependabot updates |

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

**Never expose port 80/443 to the world.** Only KMS port 1688 should be public.

```bash
cp .env.internet.example .env
# Edit .env — set strong password, place cert.pem + key.pem in ./certs/
docker compose -f compose.internet.yaml up -d
```

| Setting | Value | Why |
|---------|-------|-----|
| `KMS_BIND` | `0.0.0.0` | Windows clients connect from internet |
| `GUI_BIND` | `127.0.0.1` | Dashboard only via SSH tunnel / Tailscale |
| `NGINX_BASIC_AUTH_*` | **Required** | Enforced by `INTERNET_MODE=true` |
| `NGINX_TLS_ENABLED` | `true` | HTTPS for local GUI access |
| `DEBUG` | empty | Blocked in internet mode |

Access GUI remotely:

```bash
ssh -L 8443:127.0.0.1:443 user@your-server
# browser: https://localhost:8443
```

Or use **Tailscale** — no port forwarding for GUI.

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
| API has no separate auth token | Medium | Basic Auth; don't expose port 80 |
| KMS protocol unencrypted on 1688 | Medium | Expected for KMS; limit exposure |
| Password in env vars | Low | Docker secrets for production |
| py-kms upstream trust | Low | Commit pinned in Dockerfile |

---

## Reporting issues

Open an issue: https://github.com/kissesses/docker-kms-gui/issues

For py-kms engine vulnerabilities: https://github.com/Py-KMS-Organization/py-kms
