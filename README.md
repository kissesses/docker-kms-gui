# KMS-GUI

**Maintainer:** [kissesses](https://github.com/kissesses)

Docker stack: **KMS activation server** (py-kms, port 1688) + **web dashboard** (nginx 1.30.2, port 80/443).

> Forked from [11notes/docker-KMS-GUI](https://github.com/11notes/docker-KMS-GUI) — fully rewritten, no dependency on abandoned upstream images.

## What you get

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| **kms** | `ghcr.io/kissesses/kms` | 1688 | Windows / Office activation (KMS protocol) |
| **gui** | `ghcr.io/kissesses/kms-gui` | 80 or 443 | Dashboard, clients, products, admin panel, REST API |

Both containers share one SQLite volume (`kms-data`) — client list and admin settings persist across restarts.

---

## Requirements

### Minimum

| | |
|---|---|
| **OS** | Linux **x86_64** or **aarch64** (Docker auto-install via script; macOS/Windows — [Docker Desktop](https://www.docker.com/products/docker-desktop/)) |
| **Docker** | Engine **24.0+**, Compose plugin **v2.20+** — **installed automatically** by `install.sh` if missing (Linux) |
| **CPU** | 1 core |
| **RAM** | **512 MB** free for Docker + 2 containers |
| **Disk** | **2 GB** free (images ~300–500 MB + SQLite volume) |
| **Network** | Outbound internet for `docker compose pull` (first install) |
| **Tools** | `git`, `curl` (install script healthcheck) |

**Ports on the host** (depends on mode):

| Mode | Ports |
|------|-------|
| local | `127.0.0.1:80` (GUI), `127.0.0.1:1688` (KMS) |
| lan | `127.0.0.1:80` (GUI), `0.0.0.0:1688` (KMS) |
| internet | `0.0.0.0:443` + `80` (GUI), `0.0.0.0:1688` (KMS) |

**Internet mode additionally:** TLS certificate `cert.pem` + `key.pem` in `./certs/` (or generate a test cert via `scripts/install.sh`).

**Build from source (`--build`):** +**2 GB** disk, `git` inside Docker build, stable network (py-kms is cloned during image build).

### Recommended

| | |
|---|---|
| **CPU** | 2+ cores |
| **RAM** | **2 GB+** (comfortable headroom for Docker, nginx, gunicorn, py-kms) |
| **Disk** | **10 GB+** (image updates, logs, client database growth) |
| **Network** | Static LAN IP or DNS A-record for the server |
| **Security** | `GUI_AUTH_ENABLED=true` whenever GUI or KMS is reachable outside localhost |
| **Internet** | Valid TLS cert (Let's Encrypt, Cloudflare Origin); firewall allows **1688/tcp** and **443/tcp** only |
| **LAN** | `KMS_BIND=0.0.0.0`, `GUI_BIND=127.0.0.1` — KMS for clients, GUI not exposed to LAN |

KMS itself is lightweight (tens of clients on minimal hardware is fine). Most resource use comes from Docker and the web stack, not activation traffic.

---

## Installation

### Option A — one command (no manual clone)

```bash
curl -fsSL https://raw.githubusercontent.com/kissesses/docker-kms-gui/main/install.sh | bash
```

Interactive menu, clones to **`~/kms-gui`** automatically.

> **Note:** with `curl | bash`, answer prompts in the same terminal session (input uses `/dev/tty`). For fully non-interactive install, pass `--mode` and `--yes`:

```bash
# local, no prompts
curl -fsSL https://raw.githubusercontent.com/kissesses/docker-kms-gui/main/install.sh | bash -s -- --mode local --yes

# LAN
curl -fsSL https://raw.githubusercontent.com/kissesses/docker-kms-gui/main/install.sh | bash -s -- --mode lan --yes

# internet → /opt/kms-gui, pin image version
curl -fsSL https://raw.githubusercontent.com/kissesses/docker-kms-gui/main/install.sh | bash -s -- \
  --mode internet --dir /opt/kms-gui --version 1.8.0 --tz Europe/Moscow --yes
```

Environment alternatives: `KMS_GUI_DIR=/opt/kms-gui`, `KMS_VERSION=1.8.0`.

> **`--ref v1.8.0`** still works (treated as image version). Git clone always uses **`main`** so the installer is present.

### Option B — install script from cloned repo

```bash
git clone https://github.com/kissesses/docker-kms-gui.git
cd docker-kms-gui
./scripts/install.sh
```

Same flags as above (`--mode`, `--dir`, `--version`, `--yes`, …). Run `./scripts/install.sh --help`.

### Option C — ready-made images (manual)

```bash
git clone https://github.com/kissesses/docker-kms-gui.git
cd docker-kms-gui
cp .env.example .env
docker compose pull
docker compose up -d
```

Images are pulled from **ghcr.io/kissesses/** — no local build needed.

### Option D — build from source (manual)

```bash
git clone https://github.com/kissesses/docker-kms-gui.git
cd docker-kms-gui
cp .env.example .env
docker compose up -d --build
```

Use this if you changed code locally or need a version that is not published yet.

### Check that it works

```bash
docker compose ps          # both services should be "healthy"
curl -s http://127.0.0.1/livez   # → OK
```

Open **http://127.0.0.1** — dashboard.  
KMS endpoint for clients: **127.0.0.1:1688** (localhost only by default).

---

## After install — what to do

### 1. Activate a Windows client

On the machine you want to activate, point it to your KMS server:

```cmd
slmgr /skms YOUR_SERVER_IP:1688
slmgr /ato
```

Replace `YOUR_SERVER_IP` with the host where Docker runs (`127.0.0.1` on the same PC, or LAN IP if you opened KMS to the network — see [LAN](#lan-same-network) below).

Office (example):

```cmd
cd "C:\Program Files\Microsoft Office\Office16"
cscript ospp.vbs /sethst:YOUR_SERVER_IP
cscript ospp.vbs /act
```

GVLK keys for each product are on the **Products** page in the GUI.

### 2. Monitor clients

| Page | URL | What it shows |
|------|-----|---------------|
| Dashboard | `/` | Stats, uptime, client chart |
| Clients | `/clients` | Activated machines (auto-refreshes every 30 s) |
| Products | `/products` | GVLK keys by category (copy to clipboard) |
| License | `/license` | py-kms license text |

REST API (same data): `/api/v1/stats`, `/api/v1/clients`, `/api/v1/clients/export`, `/api/v1/activations`.

### 3. Admin panel (optional)

By default the GUI is open on localhost without login. Admin routes are **hidden** until you enable auth.

**Enable application login** — edit `.env`:

```env
GUI_AUTH_ENABLED=true
```

Restart and create the administrator on first visit:

```bash
docker compose up -d
```

1. Open **http://127.0.0.1/setup** — create account (password ≥ 12 characters)
2. Sign in at **/login**
3. Manage at **/admin**:
   - **Account** — change password
   - **Activations** — KMS policy, client bindings, renewal health, remove stale clients
   - **Security** — auth status overview
   - **Audit** — log of admin actions

> If you need `/admin` without login on a trusted LAN (not recommended on internet), set `ADMIN_PUBLIC=true`.

### 4. Change KMS limits (client count, renewal interval)

Defaults are in `.env`:

```env
KMS_CLIENT_COUNT=26
KMS_ACTIVATION_INTERVAL=120      # minutes
KMS_RENEWAL_INTERVAL=10080       # minutes (7 days)
KMS_HWID=RANDOM
```

After changing values:

```bash
docker compose up -d
docker compose restart kms
```

You can also edit policy in **Admin → Activations** (saved to `kms-policy.json`); still restart the `kms` container so py-kms picks up env changes.

---

## Deployment profiles

### Local / home (default)

Best for a single PC or home lab. GUI and KMS bound to **127.0.0.1** — not reachable from other machines.

```bash
cp .env.example .env
docker compose up -d
```

Optional extra protection — nginx Basic Auth in `.env`:

```env
NGINX_BASIC_AUTH_USER=admin
NGINX_BASIC_AUTH_PASS=your-long-random-password
```

### LAN (same network)

Allow other PCs on your network to activate:

```env
KMS_BIND=0.0.0.0          # KMS on all interfaces
GUI_BIND=127.0.0.1        # GUI stays local-only (recommended)
GUI_AUTH_ENABLED=true     # recommended if GUI is ever exposed
```

```bash
docker compose up -d
```

Clients use `slmgr /skms 192.168.x.x:1688` where `192.168.x.x` is your Docker host IP.

### Internet (KMS + GUI public)

KMS and GUI on the internet — **must** use HTTPS and application login:

```bash
cp .env.internet.example .env
mkdir -p certs
# Place cert.pem and key.pem in ./certs/
docker compose -f compose.internet.yaml pull
docker compose -f compose.internet.yaml up -d
```

First visit: **`https://your-domain/setup`** — create administrator.

| Setting | Value | Why |
|---------|-------|-----|
| `KMS_BIND` | `0.0.0.0` | Remote Windows clients |
| `GUI_BIND` | `0.0.0.0` | Web panel over HTTPS |
| `GUI_AUTH_ENABLED` | `true` | Required in internet mode |
| `NGINX_TLS_ENABLED` | `true` | Encrypt login and sessions |
| `GUI_PORT` | `443` | HTTPS |

Full checklist: [SECURITY.md](SECURITY.md).

### Sidecar nginx

External nginx in front of Gunicorn (no in-container nginx):

```bash
docker compose -f compose.sidecar.yaml up -d
```

GUI on **http://localhost:3000**. Add Basic Auth via [`nginx/sidecar-auth.conf.example`](nginx/sidecar-auth.conf.example).

---

## Update to a new version

```bash
# in .env — set new tags, e.g.:
# KMS_VERSION=1.8.0
# GUI_VERSION=1.8.0

docker compose pull
docker compose up -d
```

Data in volume `kms-data` (clients, admin account, audit log) is kept.

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `KMS_VERSION` / `GUI_VERSION` | `1.8.0` | Image tags from ghcr.io |
| `BIND_ADDRESS` | `127.0.0.1` | Default bind for both services |
| `KMS_BIND` / `GUI_BIND` | — | Override bind per service |
| `KMS_PORT` | `1688` | KMS host port |
| `GUI_PORT` | `80` | GUI host port (`443` in internet profile) |
| `TZ` | `UTC` | Timezone |
| `KMS_LOGLEVEL` | `INFO` | KMS server log level |
| `KMS_CLIENT_COUNT` | `26` | Max simultaneous KMS clients |
| `KMS_ACTIVATION_INTERVAL` | `120` | Activation interval (minutes) |
| `KMS_RENEWAL_INTERVAL` | `10080` | Renewal interval (minutes) |
| `KMS_HWID` | `RANDOM` | HWID mode for py-kms |
| `GUI_AUTH_ENABLED` | `false` | Application login (`/setup`, `/login`) |
| `ADMIN_PUBLIC` | `false` | Show `/admin` without login when auth is off |
| `NGINX_BASIC_AUTH_USER/PASS` | — | nginx Basic Auth (alternative to app login) |
| `NGINX_TLS_ENABLED` | `false` | TLS termination in GUI container |
| `TLS_CERT_DIR` | `./certs` | Host path → `/etc/nginx/certs` |
| `DEBUG` | — | Debug logs (blocked in internet mode) |

Full list: [`.env.example`](.env.example)

---

## API

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/stats` | Server statistics (JSON) |
| `GET /api/v1/clients` | Client list (JSON). Query: `q`, `app`, `status`, `health` |
| `GET /api/v1/clients/export` | CSV export |
| `GET /api/v1/activations` | Policy + client bindings + renewal health |
| `GET /api/v1/protocol` | KMS protocol overview (fields, flow, policy) |
| `GET /api/v1/clients/<id>/<app>/session` | Last known client ↔ server data exchange |
| `GET /livez` | Liveness probe |
| `GET /readyz` | Readiness probe |

When `GUI_AUTH_ENABLED=true` or `INTERNET_MODE=true`, all `/api/*` routes require a logged-in session (401 JSON if missing). `/livez` and `/readyz` stay public.

Optional automation token — set `GUI_API_TOKEN` in `.env` and pass header:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" https://your-server/api/v1/stats
```

---

## Troubleshooting

| Problem | What to check |
|---------|---------------|
| `invalid IP address: 0.0.0.0}` | Typo in `.env` — remove trailing `}` from `KMS_BIND` / `GUI_BIND`. Run `git pull` (nested compose `${…:-${…}}` fixed in v1.8.x). |
| GUI intermittently down / 502 | Low RAM (OOM), gunicorn crash, or SQLite lock — see below; check `docker compose logs gui` |
| `unknown profile` / wrong logs command | No compose profiles — use `docker compose -f compose.internet.yaml logs -f` (not `--profile`) |
| GUI not opening | `docker compose ps` — wait until `gui` is healthy; check `GUI_BIND` and port |
| Client cannot activate | Firewall on host port 1688; `KMS_BIND=0.0.0.0` for remote clients; correct IP in `slmgr /skms` |
| `/setup` redirects to dashboard | Admin already created — use `/login` |
| `/admin` redirects to dashboard | Enable `GUI_AUTH_ENABLED=true` or set `ADMIN_PUBLIC=true` |
| Policy changes not applied | Restart KMS: `docker compose restart kms`; update `.env` if you changed env vars |
| HTTPS certificate errors | Files must be named `cert.pem` and `key.pem` in `./certs/` |

Logs:

```bash
docker compose logs -f kms
docker compose logs -f gui
```

### GUI drops and recovers

Common causes on small VPS (~512 MB RAM):

1. **OOM** — kernel kills gunicorn (signal 9); container supervisor restarts it → 30–90 s outage. **Fix:** 2 GB+ RAM or swap; set in `.env`:
   ```bash
   GUNICORN_PRELOAD=false
   GUNICORN_THREADS=2
   GUNICORN_MAX_REQUESTS=0
   ```
2. **Gunicorn restart without wait** — fixed in v1.10.1+: supervisor waits for `/livez` after each restart.
3. **SQLite lock** — rare `database is locked` errors; builds retry reads automatically.

**Diagnose:**

```bash
docker compose logs gui --tail 200
docker compose exec gui cat /kms/var/gui-supervisor.log
curl -H "Cookie: session=..." https://your-server/api/v1/diagnostics   # when logged in
# or Admin → Operations → Stability diagnostics
dmesg | grep -i oom    # host OOM kills
free -h
```

---

## Build images manually

```bash
docker build -f Dockerfile.kms -t ghcr.io/kissesses/kms:1.8.0 .
docker build -f Dockerfile -t ghcr.io/kissesses/kms-gui:1.8.0 .
```

---

## Security

See [SECURITY.md](SECURITY.md) for threat model, rate limits, CSRF, and deployment checklist.

---

## Releases & CI

- [CHANGELOG.md](CHANGELOG.md) — version history  
- [RELEASE.md](RELEASE.md) — maintainer release process  

Tag `v*` on `main` triggers GitHub Actions: build → Grype scan → pytest → push to **ghcr.io/kissesses/** → GitHub Release with screenshots.

---

## Project structure

```
Dockerfile          # Web GUI image
Dockerfile.kms      # KMS server image
compose.yaml        # Default stack (local / LAN)
compose.internet.yaml
compose.sidecar.yaml
rootfs/             # nginx, entrypoint, UI, Python backend
docker/kms/         # KMS server entrypoint
tests/              # pytest (auth, activation, app)
scripts/install.sh  # installer (local / lan / internet)
install.sh        # one-liner entry (curl | bash)
.github/workflows/  # CI build & release
```

---

## Credits

- [Py-KMS-Organization/py-kms](https://github.com/Py-KMS-Organization/py-kms) — KMS engine
- [11notes/docker-KMS-GUI](https://github.com/11notes/docker-KMS-GUI) — original GUI wrapper (abandoned)
- Custom Web UI (`rootfs/kms/styles/custom-icon/`)

## License

MIT — see [LICENSE](LICENSE)
