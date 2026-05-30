#!/usr/bin/env bash
# KMS-GUI — one-liner installer (clone + setup)
# curl -fsSL https://raw.githubusercontent.com/kissesses/docker-kms-gui/main/install.sh | bash
# curl -fsSL .../install.sh | bash -s -- --mode local --yes
set -euo pipefail

readonly REPO_URL="https://github.com/kissesses/docker-kms-gui.git"
INSTALL_DIR="${KMS_GUI_DIR:-${HOME}/kms-gui}"
REPO_REF="${KMS_GUI_REF:-main}"

# Запуск из git checkout — делегируем scripts/install.sh
SELF="${BASH_SOURCE[0]:-}"
if [[ -n "${SELF}" && -f "${SELF}" ]]; then
  ROOT="$(cd "$(dirname "${SELF}")" && pwd)"
  if [[ -f "${ROOT}/compose.yaml" && -x "${ROOT}/scripts/install.sh" ]]; then
    exec bash "${ROOT}/scripts/install.sh" "$@"
  fi
fi

# curl | bash — разбор --dir / --ref до clone
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -d|--dir)
      INSTALL_DIR="${2:?}"
      shift 2
      ;;
    --ref)
      REPO_REF="${2:?}"
      shift 2
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done

command -v git >/dev/null 2>&1 || { echo "[FAIL] git не найден"; exit 1; }

if [[ -d "${INSTALL_DIR}/.git" && -f "${INSTALL_DIR}/compose.yaml" ]]; then
  :
else
  if [[ -e "${INSTALL_DIR}" ]]; then
    echo "[FAIL] ${INSTALL_DIR} существует, но не KMS-GUI — укажите --dir /другой/путь"
    exit 1
  fi
  echo "[INFO] git clone → ${INSTALL_DIR} (ref: ${REPO_REF})"
  git clone --depth 1 --branch "${REPO_REF}" "${REPO_URL}" "${INSTALL_DIR}"
fi

exec bash "${INSTALL_DIR}/scripts/install.sh" --dir "${INSTALL_DIR}" --ref "${REPO_REF}" "${ARGS[@]}"
