#!/usr/bin/env bash
# Build GUI, seed demo DB, capture screenshots with Playwright.
set -euo pipefail

OUT_DIR="${1:-screenshots}"
PORT="${2:-18080}"
DB_DIR="/tmp/kms-screenshot"
BASE_URL="http://127.0.0.1:${PORT}"

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

echo "==> Building kms-gui image for screenshots"
docker build -f Dockerfile -t kms-gui:screenshot \
  --build-arg BUILD_VERSION=screenshot \
  .

echo "==> Seeding demo database and KMS policy"
python3 scripts/seed-demo-db.py "${DB_DIR}/kms.db"

start_gui() {
  local auth_enabled="${1:-false}"
  docker rm -f kms-screenshot 2>/dev/null || true
  docker run -d --name kms-screenshot \
    -p "${PORT}:80" \
    -v "${DB_DIR}:/kms/var" \
    -e NGINX_ENABLED=true \
    -e GUI_AUTH_ENABLED="${auth_enabled}" \
    -e GUI_SECRET_KEY=screenshot-ci-secret \
    kms-gui:screenshot
}

wait_gui() {
  for i in $(seq 1 45); do
    if curl -sf "${BASE_URL}/livez" >/dev/null 2>&1; then
      echo "GUI is ready"
      return 0
    fi
    if [[ "$i" -eq 45 ]]; then
      echo "GUI failed to start" >&2
      docker logs kms-screenshot 2>&1 || true
      return 1
    fi
    sleep 2
  done
}

cleanup() {
  docker rm -f kms-screenshot 2>/dev/null || true
}
trap cleanup EXIT

echo "==> Phase 1: public pages (auth disabled)"
start_gui false
wait_gui

echo "==> Installing Playwright"
cd scripts/screenshots
if [[ ! -f package.json ]] || [[ ! -f capture.mjs ]]; then
  echo "Missing scripts/screenshots/package.json or capture.mjs" >&2
  exit 1
fi
npm install --omit=dev
npx playwright install chromium --with-deps

echo "==> Capturing public screenshots"
node capture.mjs "${BASE_URL}" "${ROOT}/${OUT_DIR}" public

echo "==> Phase 2: setup and KMS policy (auth enabled)"
cd "$ROOT"
rm -f "${DB_DIR}/gui_auth.db" "${DB_DIR}/.gui_secret"
start_gui true
wait_gui

echo "==> Capturing auth and activation policy screenshots"
node scripts/screenshots/capture.mjs "${BASE_URL}" "${ROOT}/${OUT_DIR}" auth

ls -la "${ROOT}/${OUT_DIR}"
