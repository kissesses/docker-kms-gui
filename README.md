<div align="center">

# 🗝️ KMS-GUI

**Свой KMS-сервер Windows / Office + красивая веб-панель — в двух Docker-контейнерах**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-24%2B-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/)
[![ghcr.io](https://img.shields.io/badge/ghcr.io-kissesses%2Fkms--gui-181717?logo=github)](https://github.com/kissesses/docker-kms-gui/pkgs/container/kms-gui)

Fork [11notes/docker-KMS-GUI](https://github.com/11notes/docker-KMS-GUI) · движок [py-kms](https://github.com/Py-KMS-Organization/py-kms) · maintainer [**kissesses**](https://github.com/kissesses)

**🇷🇺 [Русский](#-русский)** · **🇬🇧 [English](#-english)**

</div>

---

## ⚡ За 30 секунд

```text
┌─────────────┐     TCP 1688      ┌─────────────┐
│  Windows /  │ ───────────────►  │     kms     │  py-kms
│   Office    │                   │   :1688     │
└─────────────┘                   └──────┬──────┘
                                         │ volume kms-data
┌─────────────┐     HTTP/S 80/443 ┌──────▼──────┐
│   Браузер   │ ◄──────────────►  │     gui     │  nginx + Flask
│  админ /    │                   │  dashboard  │
│  GVLK / API │                   └─────────────┘
└─────────────┘
```

| 🐳 Сервис | 🔌 Порт | 📋 Назначение |
|-----------|---------|---------------|
| `kms` | **1688** | Активация по протоколу KMS |
| `gui` | **80** / **443** | Панель, ключи GVLK, админка, REST API |

> 💾 Оба контейнера делят volume **`kms-data`** — клиенты, политика и учётка админа переживают перезапуск.

---

## 🇷🇺 Русский

### 🚀 Быстрый старт

**Одной командой** (Linux, установщик на русском):

```bash
curl -fsSL https://raw.githubusercontent.com/kissesses/docker-kms-gui/main/scripts/install.sh | bash
```

**VPS / сервер в РФ** — типичный сценарий:

```bash
curl -fsSL https://raw.githubusercontent.com/kissesses/docker-kms-gui/main/scripts/install.sh | bash -s -- \
  --mode internet \
  --dir /opt/kms-gui \
  --tz Europe/Moscow \
  --yes
```

**Из клона репозитория:**

```bash
git clone https://github.com/kissesses/docker-kms-gui.git
cd docker-kms-gui
./scripts/install.sh              # интерактивно
./scripts/install.sh --help       # все опции
```

**Вручную без установщика:**

```bash
git clone https://github.com/kissesses/docker-kms-gui.git
cd docker-kms-gui
cp .env.example .env          # TZ=Europe/Moscow уже по умолчанию
docker compose pull && docker compose up -d
```

**Проверка:**

```bash
docker compose ps
curl -s http://127.0.0.1/livez    # → OK
```

Откройте **http://127.0.0.1** — панель. Для клиентов KMS: **`IP_СЕРВЕРА:1688`**.

---

### 🌐 Режимы развёртывания

| Режим | ⚙️ Настройка | 👤 Кому |
|-------|--------------|---------|
| 🏠 **Local** | `./scripts/install.sh --mode local` | Один ПК, `127.0.0.1` |
| 🏢 **LAN** | `./scripts/install.sh --mode lan` | KMS в сети (`KMS_BIND=0.0.0.0`) |
| 🌍 **Internet** | `./scripts/install.sh --mode internet` | VPS, HTTPS + login |

Один файл **`compose.yaml`** — режим задаётся через **`.env`** (`INTERNET_MODE`, bind, TLS).

<details>
<summary><b>🌍 Internet — пошагово</b></summary>

```bash
./scripts/install.sh --mode internet --dir /opt/kms-gui --tz Europe/Moscow --yes
# или вручную:
cp .env.example .env   # INTERNET_MODE=true, binds, TLS — см. install.sh
mkdir -p certs         # cert.pem + key.pem
docker compose pull && docker compose up -d
```

1. Первый визит → **`https://ваш-домен/setup`** — создайте администратора  
2. Вход → **`/login`**  
3. На **`/login`** доступен **подбор GVLK** и **инструкция активации** (Windows / Office)  
4. Firewall: откройте **1688/tcp** (KMS) и **443/tcp** (GUI)

📖 Чеклист безопасности: [docs/SECURITY.md](docs/SECURITY.md)

</details>

---

### 🖥️ Интерфейс на русском

| Способ | Как |
|--------|-----|
| 🔘 В панели | Кнопка **RU / EN** в шапке (переключатель языка) |
| ⚙️ По умолчанию | В `.env`: `GUI_DEFAULT_LANG=ru` → перезапуск `gui` |

Переведены: навигация, админка, модалка ключей на `/login`, подсказки активации, статусы клиентов.

---

### 🔑 Активация клиента (Windows / Office)

**Windows** — CMD от администратора:

```cmd
slmgr /ipk ВАШ_GVLK
slmgr /skms IP_СЕРВЕРА:1688
slmgr /ato
```

**Office** — из папки Office (например `Office16`):

```cmd
cscript ospp.vbs /inpkey:ВАШ_GVLK
cscript ospp.vbs /sethst:IP_СЕРВЕРА
cscript ospp.vbs /act
```

> 🗂️ **GVLK-ключи:** страница [**Keys**](/keys) или модалка на **`/login`** (публично, если `KEYS_PUBLIC=true`).

---

### 📊 Страницы панели

| Страница | Путь | Что внутри |
|----------|------|------------|
| 📈 Dashboard | `/` | Статистика, uptime |
| 💻 Clients | `/clients` | Активированные ПК |
| 🔑 Keys | `/keys` | Таблица GVLK, поиск, копирование |
| 📡 Protocol | `/protocol` | Справка по KMS |
| 🛡️ Admin | `/admin` | Политика, бэкапы, аудит *(с auth)* |

`/products` → автоматический редирект на `/keys`.

---

### 🔐 Авторизация

| Сценарий | Поведение |
|----------|-----------|
| 🏠 Localhost | GUI открыт; `/admin` скрыт без login |
| 🏢 LAN / 🌍 Internet | **`GUI_AUTH_ENABLED=true`** в `.env` |

```env
GUI_AUTH_ENABLED=true
```

```bash
docker compose up -d
```

→ **`/setup`** (первый раз) → **`/login`**

После смены политики в **Admin → Activations**:

```bash
docker compose restart kms
```

---

### 🔄 Обновление

```bash
# укажите KMS_VERSION / GUI_VERSION в .env, затем:
docker compose pull && docker compose up -d

# internet:
cd /opt/kms-gui
git pull
docker compose pull && docker compose up -d --build gui
```

> ✅ Данные в `kms-data` сохраняются.

---

### 🇷🇺 Для VPS и домашней сети в России

| 💡 Совет | Детали |
|----------|--------|
| ⏰ Часовой пояс | `TZ=Europe/Moscow` — уже в `.env.example` |
| 📍 Путь на сервере | `/opt/kms-gui` — удобно для `git pull` |
| 🔥 Firewall | `1688/tcp` — клиенты; `443/tcp` — панель |
| 💾 RAM | От **512 MB** минимум, **2 GB+** на VPS — стабильнее |
| 🐌 GUI «мигает» | См. [docs/README.md](docs/README.md) → GUNICORN_* для слабого VPS |

---

### 📚 Документация

| 📄 Документ | Содержание |
|-------------|------------|
| [docs/README.md](docs/README.md) | API, Docker, env, troubleshooting |
| [docs/SECURITY.md](docs/SECURITY.md) | Hardening, TLS, auth |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | История версий |
| [.env.example](.env.example) | Все переменные окружения |

---

## 🇬🇧 English

### 🚀 Quick start

```bash
curl -fsSL https://raw.githubusercontent.com/kissesses/docker-kms-gui/main/scripts/install.sh | bash
```

```bash
git clone https://github.com/kissesses/docker-kms-gui.git
cd docker-kms-gui
./scripts/install.sh
# or manual: cp .env.example .env && docker compose pull && docker compose up -d
curl -s http://127.0.0.1/livez    # → OK
```

### 🌐 Deployment modes

| Mode | Setup | Use case |
|------|-------|----------|
| **Local** | `./scripts/install.sh --mode local` | Same machine, `127.0.0.1` |
| **LAN** | `./scripts/install.sh --mode lan` | `KMS_BIND=0.0.0.0` for network clients |
| **Internet** | `./scripts/install.sh --mode internet` | Public HTTPS + **required** app login |

Single **`compose.yaml`** — mode is controlled via **`.env`** (`INTERNET_MODE`, bind addresses, TLS).

Internet: `./scripts/install.sh --mode internet` → TLS certs in `./certs/` → `docker compose up -d` → first visit **`/setup`**.

### 🖥️ Localization

Built-in **English / Russian** UI — toggle **EN / RU** in the header, or set `GUI_DEFAULT_LANG=ru` in `.env`.

### 🔑 Client activation

```cmd
slmgr /ipk YOUR_GVLK
slmgr /skms YOUR_KMS_HOST:1688
slmgr /ato
```

GVLK keys: **`/keys`** or the picker on **`/login`**.

### 🔐 Auth

Set `GUI_AUTH_ENABLED=true` for LAN/internet → **`/setup`** → **`/login`**. Restart `kms` after policy changes.

### 🔄 Update

```bash
docker compose pull && docker compose up -d
```

Data in volume `kms-data` is preserved.

---

<div align="center">

## 📦 Requirements

Linux **x86_64** / **aarch64** · Docker **24+** · Compose v2 · **512 MB** RAM min (**2 GB+** recommended) · **2 GB** disk

---

### 📜 License

MIT — see [LICENSE](LICENSE)

**Made with ☕ for homelab & small office**

</div>
