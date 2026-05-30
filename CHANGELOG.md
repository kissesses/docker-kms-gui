# Changelog

All notable changes to this project are documented here.  
Format based on [Keep a Changelog](https://keepachangelog.com/).

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
