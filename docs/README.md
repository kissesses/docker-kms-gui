# Documentation

Extended reference for [KMS-GUI](../README.md). Start with the root README for install and daily use.

| Document | Description |
|----------|-------------|
| [Security guide](SECURITY.md) | Threat model, TLS, auth, rate limits, checklist |
| [Changelog](CHANGELOG.md) | Version history |

---

## Configuration

Copy [`.env.example`](../.env.example) to `.env`. For internet, use `./scripts/install.sh --mode internet` or set bind/auth/TLS vars manually (see comments in `.env.example`).

| Variable | Default | Notes |
|----------|---------|--------|
| `KMS_VERSION` / `GUI_VERSION` | `1.11.0` | Image tags on ghcr.io |
| `KMS_BIND` / `GUI_BIND` | `127.0.0.1` | Use `0.0.0.0` for remote KMS or public GUI |
| `KMS_PORT` | `1688` | KMS on host |
| `GUI_HTTP_PORT` | `80` | Host port → container HTTP |
| `GUI_TLS_PORT` | `443` | Host port → container HTTPS (internet) |
| `INTERNET_MODE` | `false` | `true` for public HTTPS deployment |
| `KMS_CLIENT_COUNT` | `26` | Reported client count to activators |
| `KMS_ACTIVATION_INTERVAL` | `120` | Minutes (activation retry) |
| `KMS_RENEWAL_INTERVAL` | `10080` | Minutes (7 days) |
| `GUI_AUTH_ENABLED` | `false` | App login — **required on internet** |
| `KEYS_PUBLIC` | `true` | GVLK picker on `/login` without auth |
| `NGINX_TLS_ENABLED` | `false` | TLS in GUI container |
| `TLS_CERT_DIR` | `./certs` | `cert.pem`, `key.pem` |

Policy can also be edited in **Admin → Activations** (`kms-policy.json` on the shared volume). Restart the `kms` container after changes.

Optional API automation: `GUI_API_TOKEN` + header `Authorization: Bearer …`.

---

## REST API

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/stats` | Server statistics |
| `GET /api/v1/clients` | Client list (`q`, `app`, `status`, `health`) |
| `GET /api/v1/clients/export` | CSV export |
| `GET /api/v1/activations` | Policy + bindings + health |
| `GET /api/v1/protocol` | Protocol overview |
| `GET /api/v1/clients/<id>/<app>/session` | Last client ↔ server exchange |
| `GET /api/v1/keys/public` | Public GVLK list (if `KEYS_PUBLIC=true`) |
| `GET /api/v1/diagnostics` | Stability diagnostics (auth required) |
| `GET /livez` / `GET /readyz` | Health probes (public) |

When auth or internet mode is on, `/api/*` requires a logged-in session or `GUI_API_TOKEN`, except `/api/v1/keys/public` (if enabled).

---

## Troubleshooting

| Problem | What to check |
|---------|---------------|
| GUI not opening | `docker compose ps` — wait for `healthy`; `GUI_BIND`, port, firewall |
| Client cannot activate | Host firewall **1688/tcp**; `KMS_BIND=0.0.0.0`; correct IP in `slmgr /skms` |
| `/setup` → dashboard | Admin exists — use `/login` |
| `/admin` → dashboard | Set `GUI_AUTH_ENABLED=true` or `ADMIN_PUBLIC=true` |
| Policy not applied | `docker compose restart kms`; check `kms-policy.json` |
| HTTPS errors | `cert.pem` + `key.pem` in `./certs/` |
| GUI drops / 502 | Low RAM (OOM), gunicorn timeout — see below |

**Logs:**

```bash
docker compose logs -f kms
docker compose logs -f gui
docker compose exec gui cat /kms/var/gui-supervisor.log
```

**Small VPS (512 MB):** set in `.env`:

```env
GUNICORN_PRELOAD=false
GUNICORN_WORKERS=2
GUNICORN_THREADS=2
GUNICORN_TIMEOUT=300
```

Admin → **Operations** shows memory, restarts, worker timeouts, slow log.

---

## Docker images

Single [Dockerfile](../Dockerfile) with multi-stage targets:

| Target | Image | Contents |
|--------|-------|----------|
| `kms` | `ghcr.io/kissesses/kms` | py-kms, port 1688, volume `/kms/var` |
| `gui` | `ghcr.io/kissesses/kms-gui` | nginx + gunicorn/Flask UI, ports 80/443 |

**Build args** (optional):

| Arg | Default | Purpose |
|-----|---------|---------|
| `BUILD_VERSION` | `dev` | Tag written to `/VERSION` or `/opt/py-kms/VERSION` |
| `PYKMS_COMMIT` | pinned hash | py-kms git commit (reproducible builds) |
| `NGINX_VERSION` | `1.30.2` | GUI image only |

Compose passes `BUILD_VERSION` from `KMS_VERSION` / `GUI_VERSION` in `.env`.

## Build from source

```bash
docker compose up -d --build
# or
docker build --target kms --build-arg BUILD_VERSION=local -t ghcr.io/kissesses/kms:local .
docker build --target gui --build-arg BUILD_VERSION=local -t ghcr.io/kissesses/kms-gui:local .
```

---

## CI & releases

Push tag `v*` on `main` → GitHub Actions: build, Grype scan, pytest, push to **ghcr.io/kissesses/**, GitHub Release.
