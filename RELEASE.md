# Release guide

Maintainer: **kissesses**

## Before each release

1. Update version in:
   - [`.json`](.json) → `"version"`
   - [`.env.example`](.env.example) → `KMS_VERSION`, `GUI_VERSION`
   - [`compose.yaml`](compose.yaml) / [`compose.sidecar.yaml`](compose.sidecar.yaml) → defaults

2. Add a section to [`CHANGELOG.md`](CHANGELOG.md):

```markdown
## [1.5.2] — YYYY-MM-DD

### Added
- ...

### Security
- ...

### Changed
- ...
```

3. Commit and push to `main`.

## Publish

```bash
git tag v1.5.1
git push origin v1.5.1
```

GitHub Actions will:

1. Build `ghcr.io/kissesses/kms:X.Y.Z` and `ghcr.io/kissesses/kms-gui:X.Y.Z` (amd64 + arm64)
2. Push to **GitHub Container Registry**
3. Capture **screenshots** of the Web GUI (Playwright)
4. Create a GitHub Release with notes from `CHANGELOG.md` + embedded screenshots

## Preview release notes locally

```bash
.github/scripts/release-notes.sh v1.6.0
```

With screenshot links (for preview after assets exist):

```bash
INCLUDE_SCREENSHOTS=1 GITHUB_REPOSITORY=kissesses/docker-kms-gui \
  .github/scripts/release-notes.sh v1.6.0
```

## Capture screenshots locally

Requires Docker and Node.js 20+:

```bash
chmod +x .github/scripts/capture-screenshots.sh
.github/scripts/capture-screenshots.sh screenshots
open screenshots/dashboard.png
```

## Make packages public (first time)

After first push, open **GitHub → Packages** and set visibility to **Public** for `kms` and `kms-gui`.

## Daily changes (no release)

```bash
git add .
git commit -m "Describe your change"
git push origin main
```

Images are published only on **tag push** (`v*`) or manual **workflow_dispatch**.
