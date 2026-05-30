# Changelog

All notable changes to this project are documented here.  
Format based on [Keep a Changelog](https://keepachangelog.com/).

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
