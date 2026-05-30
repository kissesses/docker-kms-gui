#!/usr/bin/env bash
# Generate GitHub Release body from docs/CHANGELOG.md for a given tag (e.g. v1.6.0)
set -euo pipefail

TAG="${1:-}"
CHANGELOG="${2:-docs/CHANGELOG.md}"

if [[ -z "$TAG" ]]; then
  echo "Usage: release-notes.sh <tag> [changelog-file]" >&2
  exit 1
fi

VERSION="${TAG#v}"
export RELEASE_TAG="$TAG"
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

print("\n---\n")
print("## 📸 Screenshots\n")
shots = [
    ("dashboard.png", "Dashboard — overview and KMS status"),
    ("dashboard-light.png", "Dashboard (light theme)"),
    ("clients.png", "Clients — activated machines"),
    ("keys.png", "GVLK keys — picker and activation guide"),
    ("protocol.png", "Protocol — KMS activation flow"),
    ("login-keys.png", "Login — GVLK modal with Windows/Office guide"),
    ("setup.png", "First-run admin setup"),
    ("admin-activations.png", "Admin — KMS activation policy"),
]
repo = os.environ.get("GITHUB_REPOSITORY", "kissesses/docker-kms-gui")
tag = os.environ.get("RELEASE_TAG", f"v{version}")
for fname, caption in shots:
    url = f"https://github.com/{repo}/releases/download/{tag}/{fname}"
    print(f"### {caption}\n")
    print(f"![{caption}]({url})\n")

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
print("Read [SECURITY.md](https://github.com/kissesses/docker-kms-gui/blob/main/docs/SECURITY.md) before exposing to a network.\n")
print("## 📋 Full changelog\n")
print(f"[CHANGELOG.md](https://github.com/kissesses/docker-kms-gui/blob/main/docs/CHANGELOG.md)")
PY
