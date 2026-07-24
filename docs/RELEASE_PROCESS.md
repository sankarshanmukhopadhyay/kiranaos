---
layout: default
title: Release Process
parent: Releases
nav_order: 1
permalink: /releases/process/
---

# Release Process

## Pre-release checks

Run the following from the repository root:

```bash
make lint
make test
cd frontend && npm run build
```

## Release checklist

- Version numbers are aligned in backend metadata, frontend package metadata, and release notes.
- `CHANGELOG.md` includes the release.
- `docs/RELEASE_NOTES_vX.Y.Z.md` exists.
- `ROADMAP.md` reflects the current and next release scope.
- `.env.example` includes new settings.
- Database migrations exist for schema changes.
- Known limitations are documented.
- No README links point to missing files.

## Archive creation

From the parent directory of the repository:

```bash
zip -r kiranaos-vX.Y.Z.zip kiranaos-main \
  -x '*/node_modules/*' '*/dist/*' '*/.pytest_cache/*' '*/__pycache__/*' '*.DS_Store'
```
