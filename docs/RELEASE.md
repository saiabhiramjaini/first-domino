# Releasing the SDK

The `first-domino` Python SDK lives in `server/packages/first-domino/` and is published to
[PyPI](https://pypi.org/project/first-domino/) by `.github/workflows/sdk-release.yml` when a
tag like `sdk-v0.1.0` is pushed. Publishing uses PyPI trusted publishing, so no PyPI token is
stored in GitHub.

## One-time setup

1. Sign in to [pypi.org](https://pypi.org) and open **Your account › Publishing**.
2. Add a **pending publisher** (GitHub):
   - PyPI project name: `first-domino`
   - Owner: `saiabhiramjaini`
   - Repository: `first-domino`
   - Workflow: `sdk-release.yml`
   - Environment: `pypi`
3. In GitHub, **Settings › Environments**, create an environment named `pypi`. Optionally add
   yourself as a required reviewer, so every release waits for your click.

## Each release

1. Bump `version` in `server/packages/first-domino/pyproject.toml` and merge to `main`.
2. Tag that commit and push the tag:

   ```bash
   git tag sdk-v0.1.1
   git push origin sdk-v0.1.1
   ```

3. The workflow runs the SDK checks, builds, checks that the tag matches the version, and
   publishes. A version can be published only once; to fix a bad release, bump the version.

## Try a build locally

```bash
cd server
uv build --package first-domino --out-dir dist
uvx twine check --strict dist/*
```
