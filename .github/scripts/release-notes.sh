#!/usr/bin/env bash
# Generate GitHub Release body from CHANGELOG.md for a given tag (e.g. v1.6.0)
set -euo pipefail

TAG="${1:-}"
CHANGELOG="${2:-CHANGELOG.md}"

if [[ -z "$TAG" ]]; then
  echo "Usage: release-notes.sh <tag> [changelog-file]" >&2
  exit 1
fi

VERSION="${TAG#v}"
export RELEASE_TAG="$TAG"
export INCLUDE_SCREENSHOTS="${INCLUDE_SCREENSHOTS:-0}"
export GITHUB_REPOSITORY="${GITHUB_REPOSITORY:-kissesses/docker-kms-gui}"

if [[ ! -f "$CHANGELOG" ]]; then
  echo "Release ${TAG}"
  echo
  echo "See commit history for details."
  exit 0
fi

python3 - "$VERSION" "$CHANGELOG" <<'PY'
import os, re, sys

version = sys.argv[1]
path = sys.argv[2]
text = open(path, encoding="utf-8").read()

pattern = rf"## \[{re.escape(version)}\][^\n]*\n(.*?)(?=\n## \[|\Z)"
match = re.search(pattern, text, re.DOTALL)
if not match:
    print(f"# 🚀 Release v{version}\n\nNo changelog entry found for `{version}`.\n")
else:
    body = match.group(1).strip()
    print(f"# 🚀 Release v{version}\n")
    print(f"> Personal KMS stack by [kissesses](https://github.com/kissesses)\n")
    print(body)

if os.environ.get("INCLUDE_SCREENSHOTS") == "1":
    repo = os.environ.get("GITHUB_REPOSITORY", "kissesses/docker-kms-gui")
    tag = os.environ.get("RELEASE_TAG", f"v{version}")
    base = f"https://github.com/{repo}/releases/download/{tag}"
    print("\n---\n")
    print("## 📸 Screenshots\n")
    shots = [
        ("dashboard.png", "Dashboard"),
        ("dashboard-light.png", "Dashboard — light theme"),
        ("clients.png", "Clients"),
        ("products.png", "Products"),
        ("setup.png", "Initial setup — create administrator"),
        ("admin-activations.png", "KMS activation policy & client bindings"),
    ]
    for fname, title in shots:
        print(f"<details open>\n<summary><strong>{title}</strong></summary>\n\n")
        print(f"![{title}]({base}/{fname})\n\n</details>\n")

print("\n---\n")
print("## 📦 Docker images\n")
print("| Service | Image |")
print("|---------|-------|")
print(f"| KMS server | `ghcr.io/kissesses/kms:{version}` |")
print(f"| Web GUI | `ghcr.io/kissesses/kms-gui:{version}` |")
print("\n```bash")
print("docker compose pull")
print("docker compose up -d")
print("```\n")
print("## 🔒 Security\n")
print("Read [SECURITY.md](https://github.com/kissesses/docker-kms-gui/blob/main/SECURITY.md) before exposing to a network.\n")
print("## 📋 Full changelog\n")
print(f"[CHANGELOG.md](https://github.com/kissesses/docker-kms-gui/blob/main/CHANGELOG.md)")
PY
