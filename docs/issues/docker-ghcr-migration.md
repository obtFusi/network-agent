# Migration: Docker Image zu ghcr.io

**Status:** Geplant (nicht implementiert)
**Issue:** Teil von #48

## Problem

Aktuell wird das `network-agent` Docker-Image während des Appliance-Builds gebaut:
1. Source-Code wird in Appliance kopiert
2. `docker compose build` baut Image in der VM
3. Build dauert lange (~10 min extra)

## Lösung: Pre-built Image auf ghcr.io

### Vorteile
- Schnellerer Appliance-Build (nur `docker compose pull`)
- Unabhängige Versionierung von Image und Appliance
- Image kann separat getestet werden
- Weniger Komplexität im Packer-Template

### Neue Dateien

#### `.github/workflows/docker-build.yml`
```yaml
name: Docker Build

on:
  push:
    branches: [main]
    paths:
      - 'cli.py'
      - 'agent/**'
      - 'tools/**'
      - 'requirements.txt'
      - 'infrastructure/docker/net-agent/**'
  workflow_dispatch:
    inputs:
      version:
        description: 'Version tag (e.g., 0.4.0)'
        required: true

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4

      - name: Login to ghcr.io
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          file: infrastructure/docker/net-agent/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}/network-agent:${{ inputs.version || 'latest' }}
            ghcr.io/${{ github.repository }}/network-agent:latest
```

### Änderungen

#### `infrastructure/docker/docker-compose.yml`
```diff
services:
  net-agent:
-    build:
-      context: .
-      dockerfile: net-agent/Dockerfile
-    image: network-agent:${VERSION:-latest}
+    image: ghcr.io/obtfusi/network-agent:${VERSION:-latest}
```

#### `infrastructure/packer/network-agent.pkr.hcl`
Entfernen:
- File Provisioner für cli.py, requirements.txt, agent/, tools/
- `docker compose build` Step

Behalten:
- `docker compose pull --ignore-buildable`

### CLAUDE.md Update

Quick Reference hinzufügen:
```markdown
| Docker Image Build | `gh workflow run docker-build.yml -f version=X.Y.Z` |
```

## Implementation Steps

1. [ ] `.github/workflows/docker-build.yml` erstellen
2. [ ] docker-compose.yml anpassen (ghcr.io URL)
3. [ ] Packer Template vereinfachen (Source-Code entfernen)
4. [ ] CLAUDE.md aktualisieren
5. [ ] Testen: Docker-Build Workflow
6. [ ] Testen: Appliance-Build mit ghcr.io Image
