# Security guide

Personal deployment checklist for **kissesses/docker-kms-gui**.

## Threat model

This stack is designed for **home / lab use**:

- KMS activation server (port 1688)
- Web dashboard with client data and REST API
- Shared SQLite database between containers

**Do not expose directly to the public internet without hardening.**

---

## Current security measures

| Layer | Protection |
|-------|------------|
| nginx 1.30.2 | CVE-2026-9256 patched; no risky rewrite rules |
| Reverse proxy | Gunicorn on `127.0.0.1:8080` only (default mode) |
| Headers | CSP, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy |
| API | Rate limit 30 req/s on `/api/` |
| TLS | Optional; HSTS when TLS enabled |
| Auth | Optional HTTP Basic Auth via nginx |
| Build | py-kms pinned to specific commit (supply chain) |

---

## Recommended settings (personal use)

### 1. Bind to localhost only

In `.env`:

```env
BIND_ADDRESS=127.0.0.1
```

Default in `compose.yaml` — services not reachable from LAN/internet.

To allow LAN access intentionally: `BIND_ADDRESS=0.0.0.0`

### 2. Enable Basic Auth on Web GUI

```env
NGINX_BASIC_AUTH_USER=admin
NGINX_BASIC_AUTH_PASS=your-strong-password-here
```

Without this, anyone who can reach port 80 sees all clients and can export CSV.

### 3. Do not expose KMS port publicly

Port **1688** should stay on localhost or internal Docker network.  
Only your own machines need KMS access.

### 4. Use TLS behind reverse proxy (optional)

For remote access use VPN, Tailscale, or nginx TLS with valid certificates:

```env
NGINX_TLS_ENABLED=true
# mount cert.pem and key.pem to /etc/nginx/certs/
```

### 5. Keep images updated

```bash
docker compose pull
docker compose up -d
```

Watch [GitHub Releases](https://github.com/kissesses/docker-kms-gui/releases) for security updates.

---

## Known limitations

| Risk | Severity | Mitigation |
|------|----------|------------|
| GUI container runs nginx as root | Low (local) | Acceptable for personal Docker; use localhost bind |
| API has no separate auth token | Medium | Enable Basic Auth; don't expose port 80 |
| KMS protocol unencrypted on 1688 | Medium | Localhost bind only |
| Sidecar mode: no built-in auth | Medium | Add auth to `nginx/sidecar.conf` or use in-container nginx |
| Password in env vars | Low | Visible via `docker inspect`; use Docker secrets for production |
| py-kms upstream trust | Low | Commit pinned in Dockerfile; review before updating pin |

---

## Reporting issues

Open an issue: https://github.com/kissesses/docker-kms-gui/issues

For py-kms engine vulnerabilities: https://github.com/Py-KMS-Organization/py-kms
