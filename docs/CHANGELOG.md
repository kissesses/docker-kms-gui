# Changelog

All notable changes to this project are documented here.  
Format based on [Keep a Changelog](https://keepachangelog.com/).

---

## [Unreleased]

### Changed

- Documentation moved to `docs/` (`SECURITY.md`, `CHANGELOG.md`)
- Root **README** trimmed to install and daily use; API, Docker images, troubleshooting in `docs/README.md`
- **Dockerfiles** simplified (grouped ENV, removed redundant defaults)

### Removed

- Sidecar deployment (`compose.sidecar.yaml`, `nginx/`) — use built-in nginx in the GUI container
- Release screenshot tooling (`scripts/screenshots/`, `seed-demo-db.py`, `capture-screenshots.sh`)
- Stale metadata (`.json`), unused `img/`, duplicate `favicon.ico`, `RELEASE.md` (merged into README)
- Legacy **`products.html`** and dead `/products` UI code (`/products` still redirects to `/keys`)
- Root **`install.sh`** — use **`scripts/install.sh`** only (curl one-liner and `./scripts/install.sh`)

---

## [1.10.2] — 2026-05-30

### Fixed

- **Intermittent GUI outages without container restarts** — likely gunicorn worker timeouts (master stays alive, so supervisor showed nothing). Worker timeout events now logged to `gui-supervisor.log`; default timeout raised to 300s; 2 workers by default
- **`/api/v1/stats` polling** no longer reloads full product catalog on every request (cached 5 min)
- **SQLite** client reads use 30s lock timeout instead of default 5s
- **nginx** upstream keepalive to gunicorn; proxy read timeout 330s

### Added

- **`/kms/var/gui-slow.log`** — requests slower than 2s
- Diagnostics: `worker_timeout_events`, `slow_log_tail`

---

## [1.10.1] — 2026-05-30

### Fixed

- **GUI outages every few minutes** — supervisor now waits for gunicorn after crash restart (nginx no longer proxies to dead backend)
- Safer defaults for small VPS: `GUNICORN_PRELOAD=false`, `GUNICORN_THREADS=2`, `GUNICORN_MAX_REQUESTS=0`
- Gunicorn access/error logs to Docker stdout; exit signal/code logged to `/kms/var/gui-supervisor.log`

### Added

- **Diagnostics** — Admin → Operations + `GET /api/v1/diagnostics` (memory, restarts, supervisor log)

---

## [1.10.0] — 2026-05-30

### Added

- **Protocol page** (`/protocol`) — KMS activation flow, request/response fields, policy reference
- **Client session modal** — per-client data exchange (received / sent / schedule)
- **API** — `GET /api/v1/protocol`, `GET /api/v1/clients/<id>/<app>/session`

### Changed

- **UI v2** — sidebar layout, glass cards, hero banners, cyan/indigo palette
- Dashboard links to protocol overview; clients show health badges

---

## [1.9.0] — 2026-05-30

### Added

- **Restart KMS from admin** — one-click restart when Docker socket is mounted (`OPS_DOCKER_ENABLED`)
- **Backup / restore** — download and upload tar.gz of databases and policy (`/admin/ops`)
- **Client filters** — search by status and health on Clients page; API query params `q`, `app`, `status`, `health`
- **Webhooks** — `WEBHOOK_URL` for `client_new` and `client_unhealthy` events
- **KMS policy on restart** — KMS container reads saved `kms-policy.json` on startup

### Changed

- New admin tab **Operations**
- Activations page shows restart button when policy is pending

---

## [1.8.0] — 2026-05-30

### Added

- **CSRF protection** on all POST forms (setup, login, admin, client delete, policy edit)
- **Login rate limit** — nginx `auth_limit` zone (5 req/min) on `/login` and `/setup`
- **Admin tabs** — Account, Activations, Security, Audit log
- **Policy editor** — save KMS limits to `kms-policy.json` (restart KMS to apply)
- **Audit log** — SQLite trail of admin actions at `/admin/audit`
- **Delete client** — remove stale entries from Activations tab
- **Live refresh** — clients and activations pages poll API every 30s
- **Dashboard chart** — canvas doughnut for client distribution
- **i18n** — English / Russian toggle via `/lang/<code>`
- **pytest** CI job — auth, activation, app smoke tests
- **`ADMIN_PUBLIC`** — optional admin access when app auth is disabled

### Changed

- **Refactored Flask app** — blueprints (`auth`, `pages`, `admin`, `api`), `pykms_config`, `pykms_services`
- Removed legacy `serve_count` metric from dashboard and API
- GUI container healthcheck in compose
- KMS policy env vars exposed in `compose.yaml` (`KMS_CLIENT_COUNT`, etc.)

### Security

- Admin routes hidden when auth disabled unless `ADMIN_PUBLIC=true`
- Session secret persisted to `/kms/var/.gui_secret`

---

## [1.7.2] — 2026-05-30

### Changed

- **Admin → Activations** tab — KMS policy, client↔server binding, renewal schedule and health
- **Clients** page — card grid with machine, SKU, EPID, requests, last seen
- **Products** page — GVLK cards grouped by category with copy-to-clipboard
- Release screenshots: `setup.png`, `admin-activations.png`
- **Products** page — GVLK cards grouped by category with copy-to-clipboard
- Unix timestamps display correctly in client cards

---

## [1.7.1] — 2026-05-30

### Removed

- Legacy `py-kms` UI theme and duplicate templates under `rootfs/opt/py-kms/templates/`
- Unused `pykms-frontend.css` and dead helpers in `pykms_WebUI.py`

### Fixed

- Release CI: gunicorn could not write `/kms/var/.gui_secret` on bind-mounted volumes
- `GUI_AUTH_ENABLED` now passed through `compose.yaml` (`.env` setting actually works)
- `compose.internet.yaml` reads `${GUI_AUTH_ENABLED}` from `.env`
- `.env.example` / `.env.internet.example` reorganized and aligned with compose
- Duplicate auth warning removed from entrypoint

---

## [1.7.0] — 2026-05-30

### Added

- **Application admin auth** — first-run setup at `/setup`, login at `/login`
- **Admin panel** at `/admin` — account info, change password, system overview
- Session cookies (HttpOnly, Secure with TLS, 7-day remember-me)
- Password hashing via Werkzeug (scrypt/pbkdf2)
- `GUI_AUTH_ENABLED` — app-level auth instead of nginx Basic Auth for internet

### Changed

- **`compose.internet.yaml`** — GUI public (`0.0.0.0`) with app login + TLS
- `INTERNET_MODE` now requires `GUI_AUTH_ENABLED=true` (not nginx Basic Auth)
- All pages and API protected when auth enabled (except `/livez`, `/readyz`)
- CI: Grype (Anchore) image scan + SARIF in GitHub Security; replaced Trivy after supply-chain incident

---

## [1.6.1] — 2026-05-30

### Security

- **`compose.internet.yaml`** — KMS public (`0.0.0.0:1688`), GUI localhost-only (`127.0.0.1:443`)
- **`INTERNET_MODE`** — requires Basic Auth, blocks DEBUG
- Rate limit on all GUI routes (10 req/s, brute-force protection)
- TLS block: CSP, Permissions-Policy, general rate limit
- Sidecar nginx: CSP + rate limits + auth example
- **Trivy** image scan in CI; **Dependabot** for Docker, Actions, npm
- Split **`KMS_BIND`** / **`GUI_BIND`** in compose files

### Added

- `.env.internet.example` — internet deployment template
- `nginx/sidecar-auth.conf.example` — Basic Auth for sidecar mode

---

## [1.6.0] — 2026-05-30

### Added

- **Modern Web GUI** — new design system, top navigation, SVG icons, favicon
- Live server status pill, client distribution bar, toast notifications
- Product search and one-click GVLK copy
- **Release screenshots** — Playwright captures dashboard/clients/products for GitHub Releases
- Demo database seed script for screenshot previews

### Changed

- Sidebar layout replaced with sticky **top navigation**
- Removed heavy Tailwind bundle; single cohesive `app.css`
- Light/dark theme with system-style tokens

### Fixed

- Client IP display (`lastRequestIP` mapped correctly in UI)

---

## [1.5.1] — 2026-05-30

### Security

- Web UI and KMS ports bind to **127.0.0.1** by default (local access only)
- nginx: `server_tokens off`, CSP, Permissions-Policy, HSTS on TLS
- py-kms pinned to commit `b0e1615` (reproducible builds)
- Warning in logs when Basic Auth is not configured
- Sidecar nginx: rate limiting on `/api/`

### Added

- `SECURITY.md` — security guide for personal deployment
- `CHANGELOG.md` — structured release history
- Automated release notes from changelog in CI

### Changed

- Release descriptions now generated from `CHANGELOG.md` (not generic GitHub notes)

---

## [1.5.0] — 2026-05-30

### Added

- Standalone **kissesses/kms** server image (py-kms, port 1688)
- Standalone **kissesses/kms-gui** web interface with **nginx 1.30.2**
- Dashboard, clients, products, license pages
- REST API: `/api/v1/stats`, `/api/v1/clients`, CSV export
- UI: search, filter, sort, dark mode, auto-refresh
- Sidecar nginx deployment mode (`compose.sidecar.yaml`)
- GitHub Actions CI → **ghcr.io/kissesses/** images
- Optional Basic Auth and TLS termination

### Security

- nginx **1.30.2** — fixes CVE-2026-9256 (nginx-poolslip)
- No `rewrite` rules with overlapping captures in nginx config
- Rate limiting on `/api/` endpoints
- Security headers: X-Content-Type-Options, X-Frame-Options, Referrer-Policy
- Gunicorn bound to localhost when nginx is enabled

### Changed

- Full rewrite from abandoned 11notes/docker-KMS-GUI fork
- No dependency on external `11notes/kms` parent image
- Maintainer: **kissesses**
