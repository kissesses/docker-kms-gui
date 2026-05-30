#!/usr/bin/env bash
# Generate GitHub Release body from CHANGELOG.md for a given tag (e.g. v1.5.1)
set -euo pipefail

TAG="${1:-}"
CHANGELOG="${2:-CHANGELOG.md}"

if [[ -z "$TAG" ]]; then
  echo "Usage: release-notes.sh <tag> [changelog-file]" >&2
  exit 1
fi

VERSION="${TAG#v}"

if [[ ! -f "$CHANGELOG" ]]; then
  echo "Release ${TAG}" 
  echo
  echo "See commit history for details."
  exit 0
fi

python3 - "$VERSION" "$CHANGELOG" <<'PY'
import re, sys

version = sys.argv[1]
path = sys.argv[2]
text = open(path, encoding="utf-8").read()

pattern = rf"## \[{re.escape(version)}\][^\n]*\n(.*?)(?=\n## \[|\Z)"
match = re.search(pattern, text, re.DOTALL)
if not match:
    print(f"# Release {version}\n\nNo changelog entry found for `{version}`.\n")
    sys.exit(0)

body = match.group(1).strip()
print(f"# 🚀 Release v{version}\n")
print(f"> Personal KMS stack by [kissesses](https://github.com/kissesses)\n")
print(body)
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
print("Read [SECURITY.md](SECURITY.md) before exposing to a network.\n")
print("## 📋 Full changelog\n")
print(f"[CHANGELOG.md#{version}](https://github.com/kissesses/docker-kms-gui/blob/main/CHANGELOG.md)")
PY
