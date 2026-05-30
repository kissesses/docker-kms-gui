# KMS-GUI

**Maintainer:** [kissesses](https://github.com/kissesses)

Standalone Docker stack for KMS activation server + web GUI with **nginx 1.30.2**, dashboard, REST API and modern UI.

> Forked from [11notes/docker-KMS-GUI](https://github.com/11notes/docker-KMS-GUI) — fully rewritten, no dependency on abandoned upstream images.

## Features

- **kissesses/kms** — py-kms server (port 1688)
- **kissesses/kms-gui** — web interface (port 80)
- nginx **1.30.2** reverse proxy (CVE-2026-9256 fix)
- Dashboard, clients, products, license pages
- REST API: `/api/v1/stats`, `/api/v1/clients`, CSV export
- Basic Auth, optional TLS, sidecar nginx mode
- Localhost bind by default — see [SECURITY.md](SECURITY.md)

## Quick start

```bash
git clone https://github.com/kissesses/docker-kms-gui.git
cd docker-kms-gui
cp .env.example .env
docker compose up -d --build
```

Open **http://localhost** — web GUI (bound to `127.0.0.1` by default)  
KMS clients connect to **127.0.0.1:1688**

## Compose

```yaml
services:
  kms:
    image: ghcr.io/kissesses/kms:1.5.1
    ports: ["127.0.0.1:1688:1688"]
    volumes: [kms-data:/kms/var]

  gui:
    image: ghcr.io/kissesses/kms-gui:1.5.1
    ports: ["127.0.0.1:80:80"]
    volumes: [kms-data:/kms/var]
    depends_on:
      kms:
        condition: service_healthy
```

Or build locally — see [`compose.yaml`](compose.yaml).

## Sidecar nginx

```bash
docker compose -f compose.sidecar.yaml up -d --build
```

GUI on **http://localhost:3000** via external nginx 1.30.2.

## Environment

| Variable | Default | Description |
|---|---|---|
| `BIND_ADDRESS` | 127.0.0.1 | Host bind for published ports |
| `TZ` | UTC | Timezone |
| `KMS_LOGLEVEL` | INFO | KMS server log level |
| `KMS_GUI_STYLE` | custom-icon | UI theme (`custom-icon`, `py-kms`) |
| `NGINX_ENABLED` | true | In-container nginx |
| `NGINX_BASIC_AUTH_USER/PASS` | — | Protect web UI |
| `NGINX_TLS_ENABLED` | false | TLS termination |

Full list: [`.env.example`](.env.example)

## API

| Endpoint | Description |
|---|---|
| `GET /api/v1/stats` | Server statistics (JSON) |
| `GET /api/v1/clients` | Client list (JSON) |
| `GET /api/v1/clients/export` | CSV export |
| `GET /livez` | Health check |

## Build manually

```bash
docker build -f Dockerfile.kms -t ghcr.io/kissesses/kms:1.5.1 .
docker build -f Dockerfile -t ghcr.io/kissesses/kms-gui:1.5.1 .
```

## Security

See [SECURITY.md](SECURITY.md) for personal deployment checklist.

## Releases

See [RELEASE.md](RELEASE.md) and [CHANGELOG.md](CHANGELOG.md).

```bash
git tag v1.5.1
git push origin v1.5.1
```

GitHub Actions builds and pushes both images to **ghcr.io/kissesses/**.

## CI

| Trigger | Action |
|---|---|
| Push to `main` | Build only (no publish) |
| Tag `v*` | Build + push to ghcr.io + GitHub Release |
| `workflow_dispatch` | Build + push to ghcr.io |

## Project structure

```
Dockerfile          # Web GUI image
Dockerfile.kms      # KMS server image
compose.yaml        # Default stack
compose.sidecar.yaml
rootfs/             # nginx, entrypoint, UI, backend
docker/kms/         # KMS server entrypoint
.github/workflows/  # CI build & release
```

## Credits

- [Py-KMS-Organization/py-kms](https://github.com/Py-KMS-Organization/py-kms) — KMS engine
- [11notes/docker-KMS-GUI](https://github.com/11notes/docker-KMS-GUI) — original GUI wrapper (abandoned)
- UI theme based on [fork-pykms-frontend](https://github.com/11notes/fork-pykms-frontend)

## License

MIT — see [LICENSE](LICENSE)
