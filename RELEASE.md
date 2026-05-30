# Release guide

Maintainer: **kissesses**

## Version locations

Update version in all of these before a release:

| File | Field |
|---|---|
| [`.json`](.json) | `"version"` |
| [`.env.example`](.env.example) | `KMS_VERSION`, `GUI_VERSION` |
| [`compose.yaml`](compose.yaml) | default in `${KMS_VERSION:-X.Y.Z}` |

## Release workflow

```bash
# 1. Update version numbers (see table above)
# 2. Commit
git add .
git commit -m "Release 1.5.0"
git push origin main

# 3. Tag and push
git tag v1.5.0
git push origin v1.5.0
```

GitHub Actions (`.github/workflows/build.yml`) will:

1. Build `kissesses/kms:1.5.0` and `kissesses/kms-gui:1.5.0`
2. Push to Docker Hub (amd64 + arm64)
3. Create GitHub Release with auto-generated notes

## Docker Hub secrets

Repository **Settings → Secrets and variables → Actions**:

- `DOCKERHUB_USERNAME` = `kissesses`
- `DOCKERHUB_TOKEN` = token from [hub.docker.com/settings/security](https://hub.docker.com/settings/security)

## Manual publish (without CI)

```bash
docker build -f Dockerfile.kms -t kissesses/kms:1.5.0 .
docker build -f Dockerfile   -t kissesses/kms-gui:1.5.0 .
docker login
docker push kissesses/kms:1.5.0
docker push kissesses/kms-gui:1.5.0
```

## Daily changes (no release)

```bash
git add .
git commit -m "Describe your change"
git push origin main
```

This updates the repo only — Docker images are built on **tag push** (`v*`).
