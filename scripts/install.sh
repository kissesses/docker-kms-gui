#!/usr/bin/env bash
# =============================================================================
# KMS-GUI — скрипт установки (local / LAN / internet)
#
# Репозиторий: https://github.com/kissesses/docker-kms-gui
#
# Использование:
#   A) Без clone — одной командой:
#      curl -fsSL https://raw.githubusercontent.com/kissesses/docker-kms-gui/main/install.sh | bash
#      curl -fsSL .../install.sh | bash -s -- --mode local --yes
#      curl -fsSL .../install.sh | bash -s -- --mode internet --dir /opt/kms-gui --yes
#
#   B) Из уже клонированного репозитория:
#      ./scripts/install.sh                  # интерактивный выбор режима
#      ./scripts/install.sh --mode local     # только localhost (127.0.0.1)
#      ./scripts/install.sh --mode lan       # KMS в LAN, GUI на localhost
#      ./scripts/install.sh --mode internet  # KMS + GUI в интернет (HTTPS + login)
#
# Дополнительно:
#   --dir PATH       каталог установки при auto-clone (по умолчанию ~/kms-gui)
#   --version VER    версия Docker-образов KMS/GUI (например 1.8.0)
#   --ref REF        устарело: v1.x трактуется как --version; git clone всегда main
#   --build          собрать образы локально вместо pull
#   --enable-auth    включить GUI_AUTH_ENABLED (для local/lan)
#   --yes            не спрашивать подтверждение
#   --skip-docker-install  не ставить Docker автоматически, только проверка
#   --tz Europe/Moscow
#
# Переменные окружения (альтернатива --dir / --ref):
#   KMS_GUI_DIR=/opt/kms-gui   KMS_VERSION=1.8.0
#
# ── Минимальные требования ───────────────────────────────────────────────────
#   OS:     Linux x86_64 / aarch64 (или Docker Desktop на macOS/Windows)
#   Docker: Engine 24.0+, Compose v2.20+
#   CPU:    1 ядро
#   RAM:    512 MB свободно
#   Disk:   2 GB свободно
#   Tools:  git, curl
#   Ports:  см. README — local (80+1688), lan (+1688 в LAN), internet (443+80+1688)
#
# ── Рекомендуется ────────────────────────────────────────────────────────────
#   CPU:    2+ ядра
#   RAM:    2 GB+
#   Disk:   10 GB+
#   LAN:    статический IP; GUI_AUTH_ENABLED=true
#   Internet: валидный TLS (Let's Encrypt); firewall на 443 и 1688
# =============================================================================

set -euo pipefail

# --- Константы ----------------------------------------------------------------
readonly REPO_URL="https://github.com/kissesses/docker-kms-gui.git"
readonly DEFAULT_TZ="UTC"
readonly DEFAULT_INSTALL_DIR="${KMS_GUI_DIR:-${HOME}/kms-gui}"
readonly DEFAULT_REPO_REF="${KMS_GUI_GIT_REF:-main}"

# Каталог скрипта; REPO_ROOT задаётся ниже или в ensure_repo()
SCRIPT_PATH="${BASH_SOURCE[0]:-}"
if [[ -n "${SCRIPT_PATH}" && -f "${SCRIPT_PATH}" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "${SCRIPT_PATH}")" && pwd)"
  _candidate_root="$(cd "${SCRIPT_DIR}/.." && pwd)"
else
  SCRIPT_DIR=""
  _candidate_root=""
fi
REPO_ROOT=""

# --- Параметры по умолчанию (переопределяются аргументами) --------------------
MODE=""           # local | lan | internet
BUILD=false       # pull готовых образов или локальная сборка
ENABLE_AUTH=false # GUI_AUTH_ENABLED=true
ASSUME_YES=false
TZ_VALUE="${DEFAULT_TZ}"
COMPOSE_FILE="compose.yaml"
INSTALL_DIR="${DEFAULT_INSTALL_DIR}"
REPO_REF="${DEFAULT_REPO_REF}"
SKIP_DOCKER_INSTALL=false
IMAGE_VERSION="${KMS_VERSION:-${GUI_VERSION:-}}"
DOCKER=()

# --- Цвета для вывода (если терминал поддерживает) ---------------------------
if [[ -t 1 ]]; then
  RED='\033[0;31m'
  GREEN='\033[0;32m'
  YELLOW='\033[1;33m'
  CYAN='\033[0;36m'
  BOLD='\033[1m'
  NC='\033[0m'
else
  RED='' GREEN='' YELLOW='' CYAN='' BOLD='' NC=''
fi

info()  { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[ OK ]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
fail()  { echo -e "${RED}[FAIL]${NC} $*" >&2; exit 1; }

# --- Справка ------------------------------------------------------------------
usage() {
  cat <<'EOF'
KMS-GUI installer — local / LAN / internet

Usage:
  curl -fsSL https://raw.githubusercontent.com/kissesses/docker-kms-gui/main/install.sh | bash
  curl -fsSL .../install.sh | bash -s -- --mode local --yes
  ./scripts/install.sh [options]

Options:
  -m, --mode MODE     local | lan | internet
  -d, --dir PATH      install directory when cloning (default: ~/kms-gui)
  --version, -V VER   Docker image tag for kms + kms-gui (e.g. 1.8.0)
  --ref REF           deprecated: v1.x → image version; git clone uses main
  -b, --build         build images locally instead of pull
  --enable-auth       enable GUI_AUTH_ENABLED (local/lan)
  -y, --yes           skip confirmations
  --skip-docker-install
                      do not auto-install Docker (fail if missing)
  --tz TZ             timezone (default: UTC)
  -h, --help          show this help

Environment:
  KMS_GUI_DIR         same as --dir
  KMS_VERSION         same as --version (also sets GUI_VERSION)

Environment:
  KMS_GUI_GIT_REF     git branch for clone (default: main)

Requirements (minimum):
  Docker Engine 24+, Compose v2.20+, 1 CPU, 512 MB RAM, 2 GB disk, git, curl

Recommended:
  2+ CPU, 2 GB+ RAM, 10 GB+ disk, GUI_AUTH for LAN/internet, valid TLS for internet

See README.md → Requirements for full details.
EOF
  exit "${1:-0}"
}

# --- Разбор аргументов командной строки --------------------------------------
parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -m|--mode)
        MODE="${2:?Укажите режим: local, lan или internet}"
        shift 2
        ;;
      -b|--build)
        BUILD=true
        shift
        ;;
      --enable-auth)
        ENABLE_AUTH=true
        shift
        ;;
      -y|--yes)
        ASSUME_YES=true
        shift
        ;;
      --skip-docker-install)
        SKIP_DOCKER_INSTALL=true
        shift
        ;;
      --tz)
        TZ_VALUE="${2:?Укажите timezone, например Europe/Moscow}"
        shift 2
        ;;
      -d|--dir)
        INSTALL_DIR="${2:?Укажите каталог установки, например /opt/kms-gui}"
        shift 2
        ;;
      --version|-V)
        IMAGE_VERSION="${2#v}"
        shift 2
        ;;
      --ref)
        local ref="${2:?}"
        if [[ "${ref}" =~ ^v?[0-9]+\.[0-9]+ ]]; then
          warn "--ref ${ref} → версия образов ${ref#v} (git clone: ${DEFAULT_REPO_REF})"
          IMAGE_VERSION="${ref#v}"
        else
          REPO_REF="${ref}"
        fi
        shift 2
        ;;
      -h|--help)
        usage 0
        ;;
      *)
        fail "Неизвестный аргумент: $1 (используйте --help)"
        ;;
    esac
  done

  case "${MODE}" in
    ""|local|lan|internet) ;;
    *) fail "Неверный режим: ${MODE}. Допустимо: local, lan, internet" ;;
  esac
}

# --- Ввод с терминала (curl | bash: stdin = pipe, читаем из /dev/tty) ---------
read_tty() {
  local __var="$1"
  local __prompt="$2"
  local __reply=""

  if [[ -r /dev/tty ]]; then
    read -r -p "${__prompt}" __reply </dev/tty
  elif [[ -t 0 ]]; then
    read -r -p "${__prompt}" __reply
  else
    fail "Нет интерактивного терминала (curl|bash без TTY). Укажите режим явно, например:\n  bash -s -- --mode internet --yes"
  fi
  printf -v "${__var}" '%s' "${__reply}"
}

# --- Подтверждение действия ---------------------------------------------------
confirm() {
  local prompt="$1"
  local reply=""
  if [[ "${ASSUME_YES}" == true ]]; then
    return 0
  fi
  read_tty reply "${prompt} [y/N] "
  [[ "${reply}" =~ ^[Yy]$ ]]
}

# --- root / sudo ----------------------------------------------------------------
is_root() {
  [[ "$(id -u)" -eq 0 ]]
}

run_as_root() {
  if is_root; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    fail "Нужны права root. Запустите: sudo bash scripts/install.sh …"
  fi
}

# --- Установка Docker (https://get.docker.com) ----------------------------------
install_docker() {
  command -v curl >/dev/null 2>&1 || fail "curl не найден — нужен для установки Docker."

  if [[ "$(uname -s)" == "Darwin" ]]; then
    fail "На macOS установите Docker Desktop: https://www.docker.com/products/docker-desktop/"
  fi

  if [[ "$(uname -s)" != "Linux" ]]; then
    fail "Автоустановка Docker поддерживается только на Linux."
  fi

  info "Установка Docker через get.docker.com (может занять 1–3 мин)…"

  if is_root; then
    curl -fsSL https://get.docker.com | sh
  else
    curl -fsSL https://get.docker.com | sudo sh
  fi

  run_as_root systemctl enable docker 2>/dev/null || true
  run_as_root systemctl start docker 2>/dev/null \
    || run_as_root service docker start 2>/dev/null \
    || true

  local i=0
  while [[ $i -lt 15 ]]; do
    if docker info >/dev/null 2>&1; then
      ok "Docker установлен"
      return 0
    fi
    if command -v sudo >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1; then
      ok "Docker установлен (доступ через sudo)"
      return 0
    fi
    sleep 2
    i=$((i + 1))
  done

  fail "Docker установлен, но daemon не отвечает. Проверьте: systemctl status docker"
}

install_docker_if_needed() {
  command -v docker >/dev/null 2>&1 && return 0

  if [[ "${SKIP_DOCKER_INSTALL}" == true ]]; then
    fail "Docker не найден. Установите вручную или уберите --skip-docker-install."
  fi

  if [[ "${ASSUME_YES}" == true ]]; then
    install_docker
    return 0
  fi

  if confirm "Docker не найден. Установить автоматически (get.docker.com)?"; then
    install_docker
  else
    fail "Docker обязателен. Установите: curl -fsSL https://get.docker.com | sh"
  fi
}

start_docker_daemon() {
  docker info >/dev/null 2>&1 && return 0
  command -v sudo >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1 && return 0

  info "Запуск Docker daemon…"
  run_as_root systemctl start docker 2>/dev/null \
    || run_as_root service docker start 2>/dev/null \
    || true
  sleep 2
}

setup_docker_cmd() {
  COMPOSE=()

  if docker info >/dev/null 2>&1; then
    DOCKER=(docker)
  elif command -v sudo >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1; then
    DOCKER=(sudo docker)
    warn "Используется sudo docker. Чтобы без sudo: usermod -aG docker ${USER} && newgrp docker"
  else
    return 1
  fi

  if "${DOCKER[@]}" compose version >/dev/null 2>&1; then
    COMPOSE=("${DOCKER[@]}" compose)
  elif command -v docker-compose >/dev/null 2>&1; then
    if [[ "${DOCKER[0]}" == "sudo" ]]; then
      COMPOSE=(sudo docker-compose)
    else
      COMPOSE=(docker-compose)
    fi
    warn "Используется legacy docker-compose; рекомендуется Docker Compose v2."
  else
    return 1
  fi

  return 0
}

# --- Минимальные / рекомендуемые ресурсы (предупреждения, не блокируют) ----
check_system_hints() {
  info "Проверка окружения…"

  command -v git >/dev/null 2>&1 || warn "git не найден (нужен для clone репозитория)."
  command -v curl >/dev/null 2>&1 || warn "curl не найден (healthcheck после установки может не сработать)."

  # Версия Docker Engine
  local docker_ver
  if [[ ${#DOCKER[@]} -gt 0 ]]; then
    docker_ver="$("${DOCKER[@]}" version --format '{{.Server.Version}}' 2>/dev/null || echo "0")"
  else
    docker_ver="$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "0")"
  fi
  if [[ "${docker_ver}" != "0" ]]; then
    local major="${docker_ver%%.*}"
    if [[ "${major}" -lt 24 ]]; then
      warn "Docker ${docker_ver} — рекомендуется Engine 24.0+."
    fi
  fi

  # Compose v2
  if ! docker compose version >/dev/null 2>&1; then
    warn "Docker Compose v2 (plugin) не найден — рекомендуется docker compose, не docker-compose v1."
  fi

  # RAM / disk — только Linux, мягкие пороги из README
  if [[ -r /proc/meminfo ]]; then
    local mem_kb avail_mb
    mem_kb="$(awk '/MemAvailable/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)"
    avail_mb=$((mem_kb / 1024))
    if [[ "${avail_mb}" -gt 0 && "${avail_mb}" -lt 512 ]]; then
      warn "Доступно ~${avail_mb} MB RAM — минимум 512 MB, рекомендуется 2 GB+."
    elif [[ "${avail_mb}" -gt 0 && "${avail_mb}" -lt 2048 ]]; then
      info "RAM ~${avail_mb} MB — для production рекомендуется 2 GB+."
    fi
  fi

  if command -v df >/dev/null 2>&1; then
    local free_mb
    free_mb="$(df -m "${REPO_ROOT}" 2>/dev/null | awk 'NR==2 {print $4}' || echo 0)"
    if [[ "${free_mb}" -gt 0 && "${free_mb}" -lt 2048 ]]; then
      warn "Свободно ~${free_mb} MB на диске — минимум 2 GB, рекомендуется 10 GB+."
    fi
  fi

  ok "Окружение проверено (см. README → Requirements при сомнениях)"
}

# --- Проверка зависимостей ----------------------------------------------------
check_dependencies() {
  info "Проверка Docker и Docker Compose…"

  install_docker_if_needed
  start_docker_daemon

  if ! setup_docker_cmd; then
    if is_root && [[ -n "${SUDO_USER:-}" ]] && id "${SUDO_USER}" >/dev/null 2>&1; then
      usermod -aG docker "${SUDO_USER}" 2>/dev/null || true
      warn "Пользователь ${SUDO_USER} добавлен в группу docker — выполните: newgrp docker"
    fi
    setup_docker_cmd || fail "Docker недоступен. Проверьте: systemctl status docker"
  fi

  local docker_ver
  docker_ver="$("${DOCKER[@]}" version --format '{{.Server.Version}}' 2>/dev/null || echo "?")"
  ok "Docker готов (${docker_ver})"
}

# --- Клонирование репозитория (one-liner / curl | bash) -----------------------
repo_is_valid() {
  [[ -f "${1}/compose.yaml" && -f "${1}/.env.example" ]]
}

ensure_repo() {
  if [[ -z "${REPO_ROOT}" && -n "${_candidate_root}" ]] && repo_is_valid "${_candidate_root}"; then
    REPO_ROOT="${_candidate_root}"
  fi

  if repo_is_valid "${REPO_ROOT}"; then
    cd "${REPO_ROOT}"
    ok "Рабочий каталог: ${REPO_ROOT}"
    return 0
  fi

  # Уже клонировано bootstrap-скриптом (install.sh в корне)
  INSTALL_DIR="$(cd "${INSTALL_DIR}" 2>/dev/null && pwd || echo "${INSTALL_DIR}")"
  if repo_is_valid "${INSTALL_DIR}"; then
    REPO_ROOT="${INSTALL_DIR}"
    cd "${REPO_ROOT}"
    ok "Рабочий каталог: ${REPO_ROOT}"
    return 0
  fi

  command -v git >/dev/null 2>&1 || fail "git не найден — нужен для загрузки репозитория без ручного clone."

  info "Репозиторий не найден — установка в ${INSTALL_DIR} (git: ${REPO_REF})"

  if [[ -d "${INSTALL_DIR}/.git" ]] && repo_is_valid "${INSTALL_DIR}"; then
    REPO_ROOT="${INSTALL_DIR}"
    cd "${REPO_ROOT}"
    if confirm "Каталог уже существует. Обновить из git (${REPO_REF})?"; then
      info "git fetch / checkout ${REPO_REF}…"
      git fetch --depth 1 origin "${REPO_REF}" 2>/dev/null || git fetch origin
      git checkout "${REPO_REF}" 2>/dev/null || git checkout -B "${REPO_REF}" "origin/${REPO_REF}"
      git pull --ff-only origin "${REPO_REF}" 2>/dev/null || true
      ok "Репозиторий обновлён"
    else
      ok "Используем существующий каталог без обновления"
    fi
    return 0
  fi

  if [[ -e "${INSTALL_DIR}" ]]; then
    fail "Каталог ${INSTALL_DIR} занят, но это не KMS-GUI. Укажите другой: --dir /path"
  fi

  info "git clone ${REPO_URL} → ${INSTALL_DIR}…"
  git clone --depth 1 --branch "${REPO_REF}" "${REPO_URL}" "${INSTALL_DIR}" \
    || fail "Не удалось клонировать. Проверьте сеть и ref (--ref ${REPO_REF})."

  REPO_ROOT="${INSTALL_DIR}"
  cd "${REPO_ROOT}"
  ok "Репозиторий загружен: ${REPO_ROOT}"
}

# --- Проверка layout после ensure_repo ----------------------------------------
check_repo_layout() {
  repo_is_valid "${REPO_ROOT}" || fail "compose.yaml не найден в ${REPO_ROOT}"
  cd "${REPO_ROOT}"
}

# --- Интерактивный выбор режима -----------------------------------------------
select_mode_interactive() {
  [[ -n "${MODE}" ]] && return 0

  {
    echo ""
    echo -e "${BOLD}Выберите режим установки:${NC}"
    echo "  1) local    — только этот компьютер (127.0.0.1:80 и :1688)"
    echo "  2) lan      — KMS доступен в локальной сети, GUI только на localhost"
    echo "  3) internet — KMS + GUI в интернет (HTTPS, обязательный /setup)"
    echo ""
  } >/dev/tty 2>/dev/null || {
    echo ""
    echo -e "${BOLD}Выберите режим установки:${NC}"
    echo "  1) local    — только этот компьютер (127.0.0.1:80 и :1688)"
    echo "  2) lan      — KMS доступен в локальной сети, GUI только на localhost"
    echo "  3) internet — KMS + GUI в интернет (HTTPS, обязательный /setup)"
    echo ""
  }

  local choice=""
  read_tty choice "Режим [1/2/3] (по умолчанию 1): "

  case "${choice:-1}" in
    1|local)  MODE="local" ;;
    2|lan)    MODE="lan" ;;
    3|internet) MODE="internet" ;;
    *) fail "Неверный выбор: ${choice}" ;;
  esac
}

# --- Запись/обновление переменной в .env --------------------------------------
set_env_var() {
  local key="$1"
  local value="$2"
  local file="${REPO_ROOT}/.env"

  # Убрать случайные символы из bind-адресов (типичная ошибка: 0.0.0.0})
  value="${value//$'\r'/}"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  value="${value%%\}}"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"

  if grep -q "^${key}=" "${file}" 2>/dev/null; then
    # macOS и Linux совместимая замена
    if sed --version >/dev/null 2>&1; then
      sed -i "s|^${key}=.*|${key}=${value}|" "${file}"
    else
      sed -i '' "s|^${key}=.*|${key}=${value}|" "${file}"
    fi
  else
    echo "${key}=${value}" >> "${file}"
  fi
}

# --- Починка bind-переменных в существующем .env ------------------------------
fix_env_binds() {
  local file="${REPO_ROOT}/.env"
  [[ -f "${file}" ]] || return 0
  local key val
  for key in KMS_BIND GUI_BIND BIND_ADDRESS; do
    val="$(grep -m1 "^${key}=" "${file}" 2>/dev/null | cut -d= -f2- || true)"
    [[ -n "${val}" ]] || continue
    if [[ "${val}" == *"}"* ]]; then
      warn "Исправляем ${key}=${val} → без лишних символов"
      set_env_var "${key}" "${val}"
    fi
  done
}

# --- Создание .env для выбранного режима --------------------------------------
setup_env_file() {
  local env_src=".env.example"

  if [[ "${MODE}" == "internet" ]]; then
    env_src=".env.internet.example"
    COMPOSE_FILE="compose.internet.yaml"
  fi

  if [[ -f "${REPO_ROOT}/.env" ]]; then
    warn "Файл .env уже существует."
    if confirm "Перезаписать .env из ${env_src}?"; then
      cp "${env_src}" "${REPO_ROOT}/.env"
      ok "Скопирован ${env_src} → .env"
    else
      info "Сохраняем существующий .env, применяем только ключевые настройки режима…"
    fi
  else
    cp "${env_src}" "${REPO_ROOT}/.env"
    ok "Создан .env из ${env_src}"
  fi

  # Общие настройки
  set_env_var "TZ" "${TZ_VALUE}"

  case "${MODE}" in
    local)
      set_env_var "BIND_ADDRESS" "127.0.0.1"
      set_env_var "KMS_BIND" "127.0.0.1"
      set_env_var "GUI_BIND" "127.0.0.1"
      set_env_var "GUI_PORT" "80"
      set_env_var "NGINX_TLS_ENABLED" "false"
      if [[ "${ENABLE_AUTH}" == true ]]; then
        set_env_var "GUI_AUTH_ENABLED" "true"
      else
        set_env_var "GUI_AUTH_ENABLED" "false"
      fi
      set_env_var "ADMIN_PUBLIC" "false"
      ;;

    lan)
      # KMS слушает все интерфейсы, панель — только localhost
      set_env_var "KMS_BIND" "0.0.0.0"
      set_env_var "GUI_BIND" "127.0.0.1"
      set_env_var "GUI_PORT" "80"
      set_env_var "NGINX_TLS_ENABLED" "false"
      set_env_var "GUI_AUTH_ENABLED" "true"
      set_env_var "ADMIN_PUBLIC" "false"
      info "LAN: клиенты подключаются к <IP-хоста>:1688, GUI — http://127.0.0.1/"
      ;;

    internet)
      set_env_var "KMS_BIND" "0.0.0.0"
      set_env_var "GUI_BIND" "0.0.0.0"
      set_env_var "GUI_PORT" "443"
      set_env_var "GUI_AUTH_ENABLED" "true"
      set_env_var "NGINX_TLS_ENABLED" "true"
      set_env_var "TLS_CERT_DIR" "./certs"
      ;;
  esac

  # Опционально: включить auth в local через флаг --enable-auth
  if [[ "${MODE}" == "local" && "${ENABLE_AUTH}" == true ]]; then
    set_env_var "GUI_AUTH_ENABLED" "true"
  fi

  fix_env_binds

  if [[ -n "${IMAGE_VERSION}" ]]; then
    set_env_var "KMS_VERSION" "${IMAGE_VERSION}"
    set_env_var "GUI_VERSION" "${IMAGE_VERSION}"
    info "Docker-образы: ghcr.io/kissesses/kms:${IMAGE_VERSION}, kms-gui:${IMAGE_VERSION}"
  fi
}

# --- TLS-сертификаты (internet) -----------------------------------------------
setup_tls_certs() {
  [[ "${MODE}" == "internet" ]] || return 0

  local cert_dir="${REPO_ROOT}/certs"
  mkdir -p "${cert_dir}"

  if [[ -f "${cert_dir}/cert.pem" && -f "${cert_dir}/key.pem" ]]; then
    ok "TLS: найдены certs/cert.pem и certs/key.pem"
    return 0
  fi

  warn "TLS-сертификаты не найдены в ./certs/"
  echo "  Нужны файлы: cert.pem и key.pem"
  echo "  (Let's Encrypt, Cloudflare Origin, или свой CA)"
  echo ""

  if confirm "Сгенерировать временный self-signed сертификат для теста?"; then
    local cn=""
    read_tty cn "CN / hostname (например kms.example.com): "
    cn="${cn:-localhost}"
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
      -keyout "${cert_dir}/key.pem" \
      -out "${cert_dir}/cert.pem" \
      -subj "/CN=${cn}" \
      2>/dev/null
    chmod 600 "${cert_dir}/key.pem"
    warn "Self-signed сертификат создан. Браузер покажет предупреждение — для production используйте Let's Encrypt."
    ok "Сертификат: ${cert_dir}/"
  else
    fail "Положите cert.pem и key.pem в ${cert_dir}/ и запустите скрипт снова."
  fi
}

# --- Pull или build образов ---------------------------------------------------
deploy_stack() {
  info "Compose file: ${COMPOSE_FILE}"

  if [[ "${BUILD}" == true ]]; then
    info "Сборка образов (может занять несколько минут)…"
    "${COMPOSE[@]}" -f "${COMPOSE_FILE}" up -d --build
  else
    info "Загрузка образов с ghcr.io…"
    "${COMPOSE[@]}" -f "${COMPOSE_FILE}" pull
    "${COMPOSE[@]}" -f "${COMPOSE_FILE}" up -d
  fi

  ok "Контейнеры запущены"
}

# --- Ожидание healthcheck -----------------------------------------------------
wait_for_healthy() {
  info "Ожидание готовности сервисов (до ~60 с)…"
  local i=0
  while [[ $i -lt 12 ]]; do
    if curl -sf "http://127.0.0.1/livez" >/dev/null 2>&1 \
       || curl -sf "http://127.0.0.1:80/livez" >/dev/null 2>&1; then
      ok "GUI отвечает на /livez"
      return 0
    fi
    sleep 5
    i=$((i + 1))
  done
  warn "Healthcheck не успел — проверьте: docker compose -f ${COMPOSE_FILE} ps"
}

# --- IP хоста для подсказок LAN/internet --------------------------------------
host_ip_hint() {
  local ip=""
  if command -v ip >/dev/null 2>&1; then
    ip="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1); exit}')"
  elif command -v hostname >/dev/null 2>&1; then
    ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
  fi
  echo "${ip:-<IP-вашего-сервера>}"
}

# --- Итоговые инструкции ------------------------------------------------------
print_summary() {
  local ip
  ip="$(host_ip_hint)"

  echo ""
  echo -e "${BOLD}══════════════════════════════════════════════════════════════${NC}"
  echo -e "${BOLD}  Установка завершена — режим: ${MODE}${NC}"
  echo -e "${BOLD}══════════════════════════════════════════════════════════════${NC}"
  echo ""

  case "${MODE}" in
    local)
      echo "  GUI:     http://127.0.0.1/"
      echo "  KMS:     127.0.0.1:1688"
      echo ""
      if grep -q "^GUI_AUTH_ENABLED=true" "${REPO_ROOT}/.env" 2>/dev/null; then
        echo "  Первый запуск: http://127.0.0.1/setup — создайте администратора"
        echo "  Вход:          http://127.0.0.1/login"
      else
        echo "  Панель открыта без пароля (localhost)."
        echo "  Чтобы включить login: GUI_AUTH_ENABLED=true в .env и docker compose up -d"
      fi
      ;;
    lan)
      echo "  GUI (только на сервере):  http://127.0.0.1/"
      echo "  KMS (для клиентов в LAN): ${ip}:1688"
      echo ""
      echo "  На Windows-клиенте:"
      echo "    slmgr /skms ${ip}:1688"
      echo "    slmgr /ato"
      echo ""
      echo "  Первый запуск GUI: http://127.0.0.1/setup — создайте администратора"
      ;;
    internet)
      echo "  GUI:  https://<ваш-домен>/"
      echo "  KMS:  <ваш-домен или IP>:1688"
      echo ""
      echo "  1. Откройте https://<ваш-домен>/setup — создайте администратора (пароль ≥ 12 символов)"
      echo "  2. Вход: /login"
      echo "  3. Админка: /admin → Activations, Security, Audit"
      echo ""
      echo "  На клиенте Windows:"
      echo "    slmgr /skms <ваш-домен>:1688"
      echo "    slmgr /ato"
      ;;
  esac

  echo ""
  echo "  Каталог установки: ${REPO_ROOT}"
  echo ""
  echo "  Полезные команды:"
  echo "    cd ${REPO_ROOT}"
  echo "    docker compose -f ${COMPOSE_FILE} ps"
  echo "    docker compose -f ${COMPOSE_FILE} logs -f"
  echo "    docker compose -f ${COMPOSE_FILE} logs -f gui"
  echo "    docker compose -f ${COMPOSE_FILE} pull && docker compose -f ${COMPOSE_FILE} up -d"
  echo ""
  echo "  Документация: README.md, SECURITY.md"
  echo ""
}

# --- main ---------------------------------------------------------------------
main() {
  parse_args "$@"

  echo ""
  echo -e "${BOLD}KMS-GUI installer${NC}"
  echo ""

  check_dependencies
  check_system_hints
  ensure_repo
  check_repo_layout
  select_mode_interactive

  info "Режим: ${MODE}"
  setup_env_file
  setup_tls_certs

  if ! confirm "Запустить docker compose?"; then
    info "Конфигурация сохранена в .env — запустите вручную:"
    echo "  docker compose -f ${COMPOSE_FILE} up -d"
    exit 0
  fi

  deploy_stack
  wait_for_healthy
  print_summary
}

main "$@"
