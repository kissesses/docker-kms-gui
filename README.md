# KMS-GUI

**Maintainer:** [kissesses](https://github.com/kissesses)

Docker stack: **KMS server** (Windows / Office volume activation, port **1688**) + **web dashboard** (nginx, port **80/443**).

Fork of [11notes/docker-KMS-GUI](https://github.com/11notes/docker-KMS-GUI), rewritten with a custom UI and Python backend. Images: `ghcr.io/kissesses/kms`, `ghcr.io/kissesses/kms-gui`.

| Service | Port | Role |
|---------|------|------|
| `kms` | 1688 | KMS protocol (py-kms) |
| `gui` | 80 / 443 | Dashboard, admin, REST API |

Both services share volume **`kms-data`** (clients, policy, admin DB).

---

## Requirements

- Linux **x86_64** or **aarch64**, **Docker 24+** and Compose v2
- **512 MB** RAM minimum (**2 GB+** recommended for production)
- **2 GB** free disk (images + SQLite volume)

---

## Quick start

**Installer (recommended):**

```bash
curl -fsSL https://raw.githubusercontent.com/kissesses/docker-kms-gui/main/install.sh | bash
```

Clones to `~/kms-gui` (or use `--dir /opt/kms-gui --mode internet --yes`). See `./scripts/install.sh --help`.

**Manual:**

```bash
git clone https://github.com/kissesses/docker-kms-gui.git
cd docker-kms-gui
cp .env.example .env
docker compose pull && docker compose up -d
```

**Check:**

```bash
docker compose ps
curl -s http://127.0.0.1/livez    # → OK
```

Open **http://127.0.0.1** — dashboard. KMS for clients: **`HOST:1688`**.

---

## Deployment modes

| Mode | Compose file | Typical use |
|------|--------------|-------------|
| **Local** | `compose.yaml` | Same PC, bind `127.0.0.1` (default) |
| **LAN** | `compose.yaml` | `KMS_BIND=0.0.0.0` — clients on network |
| **Internet** | `compose.internet.yaml` | HTTPS + **must** enable auth |

**Internet:**

```bash
cp .env.internet.example .env
mkdir -p certs    # cert.pem + key.pem
docker compose -f compose.internet.yaml pull
docker compose -f compose.internet.yaml up -d
```

First visit: **`https://your-domain/setup`** (create admin). Public GVLK lookup on **`/login`** when `KEYS_PUBLIC=true`.

Details: [docs/SECURITY.md](docs/SECURITY.md)

---

## Activate a client

**Windows** (CMD as Administrator):

```cmd
slmgr /ipk YOUR_GVLK
slmgr /skms YOUR_KMS_HOST:1688
slmgr /ato
```

**Office** (from Office folder, e.g. `Office16`):

```cmd
cscript ospp.vbs /inpkey:YOUR_GVLK
cscript ospp.vbs /sethst:YOUR_KMS_HOST
cscript ospp.vbs /act
```

GVLK keys: GUI → **Keys** (`/keys`) or the product picker on **`/login`**.

---

## Web UI

| Page | Path | Purpose |
|------|------|---------|
| Dashboard | `/` | Stats, uptime |
| Clients | `/clients` | Activated machines |
| Keys | `/keys` | GVLK table, copy |
| Protocol | `/protocol` | KMS flow reference |
| Admin | `/admin` | Policy, ops, audit (with auth) |

REST API: `/api/v1/stats`, `/api/v1/clients`, `/api/v1/activations`, … — see [docs/README.md](docs/README.md).

---

## Authentication

On **localhost** the GUI is open by default; `/admin` is hidden until auth is on.

For **LAN or internet**, set in `.env`:

```env
GUI_AUTH_ENABLED=true
```

Restart → **`/setup`** (first run) → **`/login`**. Change policy under **Admin → Activations**; restart `kms` after policy changes:

```bash
docker compose restart kms
```

---

## Update

```bash
# set KMS_VERSION / GUI_VERSION in .env, then:
docker compose pull && docker compose up -d
# internet:
docker compose -f compose.internet.yaml pull && docker compose -f compose.internet.yaml up -d
```

Client data in `kms-data` is preserved.

---

## Documentation

| Document | Contents |
|----------|----------|
| [docs/README.md](docs/README.md) | Docker images, API, env vars, troubleshooting |
| [docs/SECURITY.md](docs/SECURITY.md) | Hardening, TLS, auth |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | Release history |
| [.env.example](.env.example) | All configuration options |

---

## License

MIT — see [LICENSE](LICENSE). KMS engine: [Py-KMS-Organization/py-kms](https://github.com/Py-KMS-Organization/py-kms).
