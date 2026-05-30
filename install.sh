#!/usr/bin/env bash
# KMS-GUI — one-liner installer (clone + setup)
#
# curl -fsSL https://raw.githubusercontent.com/kissesses/docker-kms-gui/main/install.sh | bash
# curl -fsSL .../install.sh | bash -s -- --mode internet --dir /opt/kms-gui --version 1.8.0 --yes
#
# Git checkout is always "main" (installer + compose). Pin Docker images with --version.
set -euo pipefail

readonly REPO_URL="https://github.com/kissesses/docker-kms-gui.git"
readonly GIT_REF="${KMS_GUI_GIT_REF:-main}"
readonly INSTALLER_RAW="https://raw.githubusercontent.com/kissesses/docker-kms-gui/main/scripts/install.sh"

INSTALL_DIR="${KMS_GUI_DIR:-${HOME}/kms-gui}"
IMAGE_VERSION=""
ARGS=()

# Запуск из git checkout — делегируем scripts/install.sh
SELF="${BASH_SOURCE[0]:-}"
if [[ -n "${SELF}" && -f "${SELF}" ]]; then
  ROOT="$(cd "$(dirname "${SELF}")" && pwd)"
  if [[ -f "${ROOT}/compose.yaml" && -f "${ROOT}/scripts/install.sh" ]]; then
    exec bash "${ROOT}/scripts/install.sh" "$@"
  fi
fi

# curl | bash — разбор аргументов bootstrap
while [[ $# -gt 0 ]]; do
  case "$1" in
    -d|--dir)
      INSTALL_DIR="${2:?}"
      shift 2
      ;;
    --version|-V)
      IMAGE_VERSION="${2#v}"
      shift 2
      ;;
    --ref)
      # Обратная совместимость: --ref v1.8.0 → версия образов, не git tag
      if [[ "${2}" =~ ^v?[0-9]+\.[0-9]+ ]]; then
        echo "[WARN] --ref ${2} — это версия Docker-образов. Git clone всегда: ${GIT_REF}"
        IMAGE_VERSION="${2#v}"
      else
        echo "[WARN] --ref для git устарел; используйте KMS_GUI_GIT_REF=${2}. Clone: ${GIT_REF}"
      fi
      shift 2
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done

command -v git >/dev/null 2>&1 || { echo "[FAIL] git не найден"; exit 1; }

ensure_install_tree() {
  if [[ -d "${INSTALL_DIR}/.git" && -f "${INSTALL_DIR}/compose.yaml" ]]; then
    if [[ ! -f "${INSTALL_DIR}/scripts/install.sh" ]]; then
      echo "[INFO] install.sh отсутствует (старый tag?) — переключаем на ${GIT_REF}…"
      git -C "${INSTALL_DIR}" fetch origin "${GIT_REF}" --depth 1 2>/dev/null || git -C "${INSTALL_DIR}" fetch origin
      git -C "${INSTALL_DIR}" checkout "${GIT_REF}" 2>/dev/null || git -C "${INSTALL_DIR}" checkout -B "${GIT_REF}" "origin/${GIT_REF}"
    fi
    return 0
  fi

  if [[ -e "${INSTALL_DIR}" ]]; then
    echo "[FAIL] ${INSTALL_DIR} существует, но не KMS-GUI — укажите --dir /другой/путь"
    exit 1
  fi

  echo "[INFO] git clone → ${INSTALL_DIR} (branch: ${GIT_REF})"
  git clone --depth 1 --branch "${GIT_REF}" "${REPO_URL}" "${INSTALL_DIR}"
}

ensure_install_script() {
  mkdir -p "${INSTALL_DIR}/scripts"
  if [[ ! -f "${INSTALL_DIR}/scripts/install.sh" ]]; then
    command -v curl >/dev/null 2>&1 || { echo "[FAIL] curl не найден"; exit 1; }
    echo "[INFO] Загрузка scripts/install.sh с GitHub…"
    curl -fsSL "${INSTALLER_RAW}" -o "${INSTALL_DIR}/scripts/install.sh"
    chmod +x "${INSTALL_DIR}/scripts/install.sh"
  fi
}

ensure_install_tree
ensure_install_script

EXTRA=()
[[ -n "${IMAGE_VERSION}" ]] && EXTRA+=(--version "${IMAGE_VERSION}")

exec bash "${INSTALL_DIR}/scripts/install.sh" --dir "${INSTALL_DIR}" "${EXTRA[@]}" "${ARGS[@]}"
