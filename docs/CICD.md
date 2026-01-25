# CI/CD - Network Agent

**Last Updated:** 2026-01-25
**Status:** Production
**SSOT for:** CI/CD Pipeline, Workflow Automation, Claude Code Integration

---

## TL;DR

- **GitHub Actions:** 8 Workflows (CI, Release, CodeQL, Auto-Label, PR-Lint, Appliance-Build, Docker-Build, OVA-Build)
- **Local CI:** `act push` runs all 4 Required Checks
- **Branch Protection:** 4 Required Status Checks (lint, test, security, docker)
- **Claude Code Skills:** `/pr`, `/release`, `/merge-deps` for automated workflows
- **Global Skills:** `/claudemd`, `/impl-plan` for planning and project setup
- **Merge Rule:** NEVER `--admin`, ALWAYS `--auto` (waits for checks)

---

## Table of Contents

1. [Pipeline Overview](#1-pipeline-overview)
2. [GitHub Actions Workflows](#2-github-actions-workflows)
3. [Build Telemetry](#3-build-telemetry)
4. [CI/CD Dashboard](#4-cicd-dashboard)
5. [Local CI with act](#5-local-ci-with-act)
6. [Branch Protection](#6-branch-protection)
7. [Claude Code Integration](#7-claude-code-integration)
8. [Project-specific Skills](#8-project-specific-skills)
9. [Global Skills](#9-global-skills)
10. [Workflow Diagrams](#10-workflow-diagrams)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           NETWORK AGENT CI/CD                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  LOCAL (Developer)                 GITHUB (Remote)           RELEASE        │
│  ┌──────────────────┐           ┌──────────────────┐      ┌─────────────┐  │
│  │ 1. Write code    │           │ 5. Create PR     │      │ 8. Tag push │  │
│  │ 2. act push      │──push──►  │ 6. CI runs       │      │ 9. Release  │  │
│  │ 3. Docker build  │           │ 7. Merge (--auto)│──►   │    created  │  │
│  │ 4. Manual test   │           └──────────────────┘      └─────────────┘  │
│  └──────────────────┘                                                       │
│         │                                │                                   │
│         ▼                                ▼                                   │
│  ┌──────────────────┐           ┌──────────────────┐                        │
│  │ /impl-plan       │           │ /pr Skill        │                        │
│  │ /claudemd        │           │ /release Skill   │                        │
│  │ (Planning)       │           │ /merge-deps      │                        │
│  └──────────────────┘           └──────────────────┘                        │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════   │
│  CLAUDE CODE INTEGRATION: Skills automate every step                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Architecture Principles

| Principle | Description |
|-----------|-------------|
| **Fail Fast** | Lint before tests, tests before security, everything before Docker |
| **Required Checks** | 4 jobs must be green before merge is allowed |
| **Local = Remote** | `act push` simulates GitHub Actions exactly |
| **Skill-First** | Claude Code skills instead of manual CLI commands |
| **Evidence Required** | No merge without documented tests |

---

## 2. GitHub Actions Workflows

### 2.1 CI Workflow (`.github/workflows/ci.yml`)

**Trigger:** Push and PR on `main`
**Concurrency:** Only one workflow per branch at a time

```yaml
jobs:
  lint:        # Ruff Format + Check + Bidi-Scan
  test:        # pytest with Coverage (needs: lint)
  security:    # pip-audit on requirements.txt (needs: lint)
  docker:      # Build + Smoke-Test + Trivy (needs: lint, test, security)
```

#### Job: lint

| Step | Description |
|------|-------------|
| `ruff format --check .` | Check code formatting |
| `ruff check agent/ tools/ cli.py` | Linting (errors, warnings) |
| Bidi-Check | Detect Unicode trojans (CVE-2021-42574) |

**Bidi-Check Details:**
```bash
grep -rP '[\x{200B}-\x{200F}\x{202A}-\x{202E}\x{2066}-\x{2069}]' \
  --include='*.py' --include='*.yml' --include='*.yaml' \
  --include='*.md' --include='Dockerfile*' .
```

Scans for hidden Unicode characters that could enable code injection.

#### Job: test

```bash
pytest --cov=agent --cov=tools --cov-report=term-missing
```

Coverage for `agent/` and `tools/` directories.

#### Job: security

```bash
pip-audit -r requirements.txt
```

Checks all dependencies for known vulnerabilities.

#### Job: docker

| Step | Description |
|------|-------------|
| `docker build -t network-agent:ci .` | Build image |
| `docker run --rm network-agent:ci python cli.py --version` | Smoke test |
| Trivy Scanner | Container vulnerabilities (CRITICAL, HIGH) |

**Trivy Configuration:**
```yaml
- uses: aquasecurity/trivy-action@0.28.0
  with:
    severity: 'CRITICAL,HIGH'
    ignore-unfixed: true  # Ignore base image CVEs without fix
```

### 2.2 Release Workflow (`.github/workflows/release.yml`)

**Trigger:** Tag push (`v*`)
**Action:** Automatic GitHub Release from CHANGELOG

```yaml
steps:
  - Extract version from tag      # v0.8.0 → 0.8.0
  - Extract changelog for version # Parse CHANGELOG.md
  - Create GitHub Release         # softprops/action-gh-release@v2
```

**CHANGELOG Parsing:**
```bash
awk "/^## \[${VERSION_NUM}\]/{flag=1; next} /^## \[/{flag=0} flag" CHANGELOG.md
```

Extracts the section between `## [X.Y.Z]` and the next `## [`.

### 2.3 CodeQL Workflow (`.github/workflows/codeql.yml`)

**Trigger:** Push, PR on `main`, weekly (Sunday 00:00 UTC)
**Language:** Python
**Purpose:** Static code analysis for security vulnerabilities

```yaml
- uses: github/codeql-action/init@v4
  with:
    languages: python
- uses: github/codeql-action/analyze@v4
```

### 2.4 Auto-Label Workflow (`.github/workflows/auto-label.yml`)

**Trigger:** Issue/PR created

#### Issue Labels (automatic)

| Title contains | Labels |
|----------------|--------|
| `[bug]`, `bug:`, `fix:` | `type:bug`, `priority:high` |
| `[feature]`, `feat:` | `type:feature` |
| `[docs]`, `docs:` | `type:docs` |
| `[refactor]`, `refactor:` | `type:refactor` |
| `[ci]`, `ci:` | `type:ci` |

All issues automatically get `status:backlog`.

#### PR Labels (automatic)

| Prefix | Label |
|--------|-------|
| `feat:`, `feat(` | `type:feature` |
| `fix:`, `fix(` | `type:bug` |
| `docs:`, `docs(` | `type:docs` |
| `deps:`, `chore(deps)` | `type:deps` |
| Author `dependabot[bot]` | `type:deps` |

### 2.5 PR-Lint Workflow (`.github/workflows/pr-lint.yml`)

**Trigger:** PR opened, edited, synchronize
**Purpose:** Enforce Conventional Commits (soft enforcement)

```yaml
types: |
  feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert, deps
ignoreLabels: |
  type:deps  # Allow Dependabot PRs with "Bump X from Y to Z"
```

**Important:** NOT configured as Required Check (Dependabot compatibility).

### 2.6 Appliance Build Workflow

**Architecture:** Two-Tier Build (Base Image + Appliance Layer)
**Runner:** Self-hosted (Proxmox LXC)
**Artifact Storage:** MinIO (LAN) for fast inter-job transfer

#### Two-Tier Build Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    TWO-TIER APPLIANCE BUILD                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  BASE IMAGE (build rarely, ~40 min)                             │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ • Debian 13 (Trixie) + Docker CE                           │ │
│  │ • systemd-networkd + SSH Hardening + Kernel Tuning         │ │
│  │ • Ollama + PRE-BAKED MODELS via virtio-9p (~36 GB)         │ │
│  │ → Store in MinIO: appliance-base/                          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                   │
│  APPLIANCE LAYER (per release, ~5 min)                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ • /opt/network-agent/ (Docker Compose Files)               │ │
│  │ • Docker Images (ghcr.io) for offline operation            │ │
│  │ • First-boot Setup + Firewall Rules                        │ │
│  │ • Version-specific Configuration                           │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                   │
│              network-agent-0.10.1.qcow2 → GitHub Release        │
│                                                                  │
│  USER STARTS VM → READY APPLIANCE (no internet needed!)         │
└─────────────────────────────────────────────────────────────────┘
```

**Benefits:**
- Release builds: ~5 min instead of ~40 min
- No Debian installation per release
- No Ollama model transfers per release
- Easier debugging (Base vs. App layer separated)

#### Pre-baked Ollama Models (virtio-9p)

Ollama models are baked directly into the base image instead of copied at runtime:

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRE-BAKED MODELS APPROACH                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  RUNNER (Host)                      PACKER VM (Guest)            │
│  ┌─────────────────┐               ┌─────────────────┐          │
│  │ /opt/ollama-cache/              │ /mnt/host-cache/ │          │
│  │   models/       │───virtio-9p──▶│   (read-only)    │          │
│  │   ├── blobs/    │               │                  │          │
│  │   └── manifests/│               │       ↓ cp -r    │          │
│  └─────────────────┘               │                  │          │
│                                    │ /usr/share/ollama│          │
│                                    │   /.ollama/models│          │
│                                    └─────────────────┘          │
│                                                                  │
│  Result: Models baked directly into qcow2 image                 │
└─────────────────────────────────────────────────────────────────┘
```

**Cache Format:**
- **Old (tar.zst):** Compress → Transfer → Extract (60GB I/O)
- **New (Directory):** Direct copy via virtio-9p (20GB I/O)

**Benefits:**
- 3x less I/O (no compression/extraction)
- Faster build (~14 min for model copy)
- Simpler workflow (fewer steps)

**Cache Directory on Runner:**
```
/opt/ollama-cache/
└── models/           # Extracted Ollama models (36GB)
    ├── blobs/        # Model files
    └── manifests/    # Model metadata
```

**When to rebuild cache?**
- Ollama model change (e.g., qwen3:30b-a3b → llama3:70b)
- Ollama major version update
- Cache corruption (rm -rf /opt/ollama-cache/models/)

#### Workflows

**1. Base Image Build (rare, only for system changes):**

```bash
# Build base image (Debian + Docker + Ollama)
gh workflow run appliance-base-build.yml -f ollama_model=qwen3:30b-a3b
```

When to rebuild?
- Debian version upgrade (13.3 → 13.4)
- Docker major update
- Ollama model change
- Kernel/SSH/Network configuration changes

**2. Appliance Build (per release):**

```bash
# Build appliance (uses base image)
gh workflow run appliance-build.yml -f version=0.10.1

# With specific base image
gh workflow run appliance-build.yml -f version=0.10.1 -f base_image=debian-docker-ollama-20260125.qcow2
```

**Jobs (appliance-build.yml):**

| Job | Runner | Timeout | Description |
|-----|--------|---------|-------------|
| `validate` | ubuntu-latest | 10m | Validate Packer template + docker-compose |
| `build` | **self-hosted** | 30m | Download base + add Network Agent layer |
| `e2e-test` | **self-hosted** | 30m | Test VM, upload to Release |

**Jobs (appliance-base-build.yml):**

| Job | Runner | Timeout | Description |
|-----|--------|---------|-------------|
| `build-base` | **self-hosted** | 120m | Complete base image with Ollama |

#### MinIO Bucket Structure

```
appliance-base/
├── debian-docker-ollama-20260125.qcow2     # Base Image
├── debian-docker-ollama-20260125.qcow2.sha256
└── (older base images for rollback)

appliance-builds/
└── {version}/                              # Temp, auto-cleanup after E2E
    ├── network-agent-0.10.1.qcow2.part-aa
    ├── network-agent-0.10.1.qcow2.part-ab
    ├── ...
    └── SHA256SUMS
```

**MinIO Artifact Storage:**

| Aspect | Value |
|--------|-------|
| Server | 10.0.0.165:9000 (Proxmox LXC 160) |
| Bucket | `appliance-builds` (temp, auto-cleanup) |
| Transfer Speed | ~100 MB/s (LAN) vs ~5 MB/s (GitHub Artifacts) |

**Secrets:**
- `MINIO_ENDPOINT` - MinIO Server URL
- `MINIO_ACCESS_KEY` - Access Key
- `MINIO_SECRET_KEY` - Secret Key

**Why Self-hosted?**
- GitHub-hosted runners only have ~14GB disk (image is 30GB+)
- Packer requires KVM/QEMU (not available on GitHub-hosted)
- Ollama cache persistent on self-hosted runner

### 2.7 Docker Build Workflow (`.github/workflows/docker-build.yml`)

**Trigger:** Push on `main` (when Dockerfile, Code, Config change) or `workflow_dispatch`
**Purpose:** Push Docker image to ghcr.io

```yaml
# Manually trigger with version
gh workflow run docker-build.yml -f version=0.9.0
```

**Steps:**

| Step | Description |
|------|-------------|
| Login to ghcr.io | Authenticate with GITHUB_TOKEN |
| Extract metadata | Version from cli.py or Input |
| Build and push | Multi-tag: `version` + `latest` |

**Tags:**
- `ghcr.io/obtfusi/network-agent:0.9.0`
- `ghcr.io/obtfusi/network-agent:latest`

### 2.8 Self-hosted Runner

**Location:** Proxmox LXC 150 (`github-runner`)
**Host:** 10.0.0.69 (Proxmox)

| Resource | Value |
|----------|-------|
| OS | Debian 13 |
| RAM | 32 GB |
| CPU | 8 Cores |
| Disk | 120 GB |
| Labels | `self-hosted`, `Linux`, `X64`, `ova-builder` |

**Security (Public Repo!):**
- **Ephemeral Mode:** Runner re-registers after each job
- **Trigger Restriction:** ONLY `workflow_dispatch` + `release`, NEVER `pull_request`
- **Dedicated User:** Runs as `runner`, not as root
- **PAT in .env:** Token not stored in systemd service

**Management:**

```bash
# Check runner status
ssh root@github-runner systemctl status github-runner

# View logs
ssh root@github-runner journalctl -u github-runner -f

# Check runner in GitHub
gh api /repos/obtFusi/network-agent/actions/runners --jq '.runners[]'
```

**Scripts:**
- `infrastructure/scripts/create-runner-lxc.sh` - LXC setup on Proxmox
- `infrastructure/scripts/runner-wrapper.sh` - Ephemeral loop with token refresh

### 2.9 MinIO Artifact Storage

**Location:** Proxmox LXC 160 (`minio`)
**IP:** 10.0.0.165
**Ports:** 9000 (API), 9001 (Console)

| Resource | Value |
|----------|-------|
| OS | Debian 12 |
| RAM | 2 GB |
| CPU | 2 Cores |
| Disk | 50 GB |
| Bucket | `appliance-builds` (temp, auto-cleanup after E2E) |

**Why MinIO instead of GitHub Artifacts?**

| Aspect | GitHub Artifacts | MinIO |
|--------|------------------|-------|
| Upload Speed | ~5 MB/s (Rate-Limited) | ~100 MB/s (LAN) |
| 27 GB Upload | ~75 min | ~5 min |
| Cost | Free (2 GB limit) | Free (self-hosted) |
| Control | GitHub managed | Self-managed |

**Management:**

```bash
# Check MinIO status
ssh root@10.0.0.69 "pct exec 160 -- systemctl status minio"

# View bucket contents
ssh root@10.0.0.69 "pct exec 160 -- /usr/local/bin/mc ls local/appliance-builds/"

# Manual cleanup
ssh root@10.0.0.69 "pct exec 160 -- /usr/local/bin/mc rm --recursive --force local/appliance-builds/OLD_VERSION/"

# Console (Web UI)
# http://10.0.0.165:9001 (minioadmin / [see Secrets])
```

**Troubleshooting:**

| Problem | Solution |
|---------|----------|
| MinIO not reachable | `pct start 160` on Proxmox |
| Upload fails | Check secrets, test network |
| Bucket full | `mc rm --recursive minio/appliance-builds/OLD_VERSION/` |
| Credentials forgotten | `ssh root@10.0.0.69 "pct exec 160 -- cat /etc/minio.env"` |

---

## 3. Build Telemetry

The telemetry system tracks detailed metrics for each build step for optimization.

### 3.1 What is measured?

| Metric | Description |
|--------|-------------|
| **Duration** | Time in seconds per step |
| **CPU%** | Average CPU utilization |
| **Memory** | RAM usage (absolute + delta) |
| **Disk Read/Write** | MB read/written + IOPS |
| **Network RX/TX** | MB received/sent + rate |

### 3.2 Telemetry Components

| Component | Path | Purpose |
|-----------|------|---------|
| GitHub Actions Telemetry | `infrastructure/scripts/telemetry.sh` | Track workflow steps |
| Packer Telemetry | `infrastructure/packer/scripts/packer-telemetry.sh` | Track provisioner steps |
| Report Tool | `infrastructure/scripts/telemetry-report.sh` | Analyze historical data |

### 3.3 Persistent Storage

Telemetry data is stored in MinIO:

```
appliance-telemetry/
├── latest/                     # Quick access to current builds
│   ├── build_0.10.1.json
│   └── e2e_0.10.1.json
└── {version}/{timestamp}/      # Complete history
    ├── build_telemetry.json
    └── e2e_telemetry.json
```

### 3.4 Usage

```bash
# Show latest build telemetry
./infrastructure/scripts/telemetry-report.sh latest

# List all available telemetry data
./infrastructure/scripts/telemetry-report.sh list

# Compare two versions
./infrastructure/scripts/telemetry-report.sh compare 0.10.1 0.10.2

# Show last N builds
./infrastructure/scripts/telemetry-report.sh history 5
```

### 3.5 Output Example

```
╔═══════════════════════════════════════════════════════════════════════╗
║                    BUILD TELEMETRY SUMMARY                            ║
╠═══════════════════════════════════════════════════════════════════════╣
║ Step1_Base_packages          45s  CPU: 32%  Net:  120MB  Disk:  200MB ║
║ Step2_Docker_CE             180s  CPU: 28%  Net:  450MB  Disk:  800MB ║
║ Step7a_Download_Models       60s  CPU:  5%  Net:15000MB  Disk:   10MB ║
║ Step7c_Ollama_Install       300s  CPU: 85%  Net:   50MB  Disk:25000MB ║
║ Step12_Docker_Pull          120s  CPU: 15%  Net: 2000MB  Disk: 3000MB ║
╠═══════════════════════════════════════════════════════════════════════╣
║ TOTAL BUILD TIME:           900s                                      ║
╚═══════════════════════════════════════════════════════════════════════╝

Bottleneck Analysis:
  Slowest step: Step7c_Ollama_Install: 300s
  Most network I/O: Step7a_Download_Models: 15000MB downloaded
  Most disk I/O: Step7c_Ollama_Install: 25000MB written
  Peak memory: Step7c_Ollama_Install: 8192MB
```

### 3.6 Bottleneck Detection

The system automatically identifies:

| Bottleneck | Indicator | Typical Cause |
|------------|-----------|---------------|
| **CPU-Bound** | CPU > 80% | Compilation, model loading |
| **I/O-Bound** | Disk Write > 100 MB/s | Extraction, image build |
| **Network-Bound** | Net RX > 50 MB/s | Model download, Docker pull |
| **Memory Pressure** | Memory Delta > 4GB | Ollama model loading |

### 3.7 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEMETRY_DIR` | `/tmp/telemetry` | Local directory for JSON data |
| `TELEMETRY_BUCKET` | `appliance-telemetry` | MinIO bucket name |
| `MINIO_ENDPOINT` | (Secret) | MinIO server URL |
| `MINIO_ACCESS_KEY` | (Secret) | MinIO access key |
| `MINIO_SECRET_KEY` | (Secret) | MinIO secret key |

---

## 4. CI/CD Dashboard

The CI/CD Dashboard provides a web interface for monitoring and controlling CI/CD pipelines with approval gates.

### 4.1 Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CI/CD DASHBOARD ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  GitHub                  Dashboard Backend              Dashboard Frontend   │
│  ┌──────────────┐       ┌──────────────────┐          ┌──────────────────┐  │
│  │ Push/PR      │       │ FastAPI          │          │ React SPA        │  │
│  │ Webhook      │──────▶│ ├─ /api/v1/...   │◀────────▶│ ├─ Pipeline List │  │
│  │              │       │ ├─ /health       │   SSE    │ ├─ Step Details  │  │
│  │ Actions      │       │ └─ SQLite DB     │          │ └─ Approvals     │  │
│  │ (Runners)    │       └──────────────────┘          └──────────────────┘  │
│  └──────────────┘               │                                           │
│                                 ▼                                           │
│                          ┌──────────────┐                                   │
│                          │ Approval     │                                   │
│                          │ Gates        │                                   │
│                          └──────────────┘                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Components

| Component | Path | Description |
|-----------|------|-------------|
| Backend | `infrastructure/cicd-dashboard/` | FastAPI + SQLite |
| Compose | `infrastructure/docker/docker-compose.dashboard.yml` | Docker service |
| CI | `.github/workflows/ci-dashboard.yml` | Lint, test, Docker build |

### 4.3 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check for Docker/K8s probes |
| GET | `/api/v1/pipelines` | List all pipelines (paginated) |
| GET | `/api/v1/pipelines/{id}` | Pipeline details with steps |
| POST | `/api/v1/pipelines` | Create new pipeline (manual trigger) |
| POST | `/api/v1/webhooks/github` | Receive GitHub webhooks |
| GET | `/api/v1/webhooks/events` | List webhook events (debug) |
| GET | `/api/v1/webhooks/events/{id}` | Webhook event details |

### 4.4 Data Models

**Pipeline States:**
- `pending` - Pipeline created, not yet started
- `running` - Pipeline execution in progress
- `waiting_approval` - Blocked on approval gate
- `completed` - All steps finished successfully
- `failed` - One or more steps failed
- `aborted` - Pipeline was cancelled

**Step States:**
- `pending` - Step not yet started
- `running` - Step in progress
- `completed` - Step finished successfully
- `failed` - Step encountered error
- `skipped` - Step skipped (dependency failed)

### 4.5 Usage

```bash
# Start with dashboard (in addition to main services)
docker compose -f docker-compose.yml -f docker-compose.dashboard.yml up -d

# Check health
curl http://localhost:8081/health

# List pipelines
curl http://localhost:8081/api/v1/pipelines

# Create manual pipeline
curl -X POST http://localhost:8081/api/v1/pipelines \
  -H "Content-Type: application/json" \
  -d '{"repo": "obtFusi/network-agent", "ref": "main", "trigger": "manual"}'
```

### 4.6 GitHub Webhook Integration

The dashboard receives GitHub webhooks to automatically trigger pipelines.

**Supported Events:**

| Event | Action | Pipeline Trigger |
|-------|--------|------------------|
| `issues` | `labeled` (status:ready) | New pipeline |
| `pull_request` | `closed` + merged | PR merged pipeline |
| `release` | `published` | Release pipeline |
| `workflow_run` | `completed` | Update step status |

**GitHub Webhook Setup:**

1. Go to Repository Settings → Webhooks → Add webhook
2. Configure:
   ```
   Payload URL: https://your-dashboard.example.com/api/v1/webhooks/github
   Content type: application/json
   Secret: <generate secure secret>
   Events: Issues, Pull requests, Releases, Workflow runs
   ```
3. Set `GITHUB_WEBHOOK_SECRET` in dashboard environment

**Local Testing:**

```bash
# Test webhook without signature (only when secret not configured)
curl -X POST http://localhost:8081/api/v1/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: issues" \
  -H "X-GitHub-Delivery: test-$(date +%s)" \
  -d '{"action":"labeled","label":{"name":"status:ready"},"issue":{"number":1,"title":"Test"},"repository":{"full_name":"test/repo"}}'
```

### 4.7 Pipeline Orchestration

The dashboard includes a full pipeline orchestration engine for managing multi-stage CI/CD pipelines.

**Pipeline State Machine:**

```
                ┌─────────────┐
                │   PENDING   │
                └──────┬──────┘
                       │ start()
                       ▼
                ┌─────────────┐
     ┌─────────│   RUNNING   │─────────┐
     │         └──────┬──────┘         │
     │                │                │
fail()│          wait_approval()  complete()
     │                │                │
     ▼                ▼                ▼
┌──────────┐   ┌───────────────┐   ┌───────────┐
│  FAILED  │   │   WAITING     │   │ COMPLETED │
└──────────┘   │   APPROVAL    │   └───────────┘
               └───────┬───────┘
                       │
          ┌────────────┼────────────┐
          │            │            │
     approve()    reject()      timeout()
          │            │            │
          ▼            ▼            ▼
    ┌─────────┐  ┌─────────┐  ┌─────────┐
    │ RUNNING │  │ FAILED  │  │ TIMEOUT │
    └─────────┘  └─────────┘  └─────────┘

Jederzeit: abort() → ABORTED
```

**Pipeline Stages:**

| Stage | Steps | Failure Behavior |
|-------|-------|------------------|
| `validate` | lint, test, security, docker-build | Abort pipeline |
| `review` | create-pr, wait-ci, pr-merge (approval) | Notify only |
| `release` | create-release (approval), docker-push, appliance-build, close-issue | Rollback |

**API Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/pipelines/{id}/start` | Start pipeline execution |
| POST | `/api/v1/pipelines/{id}/abort` | Abort running pipeline |
| POST | `/api/v1/pipelines/{id}/retry/{step_id}` | Retry failed step |
| GET | `/api/v1/pipelines/running` | List running pipelines |
| GET | `/api/v1/approvals/pending` | Get pending approvals |
| GET | `/api/v1/approvals/{id}` | Get approval details |
| POST | `/api/v1/approvals/{id}/approve` | Approve request |
| POST | `/api/v1/approvals/{id}/reject` | Reject request |

**Configuration:**

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `GITHUB_TOKEN` | PAT for GitHub API calls | required |
| `APPROVAL_TIMEOUT_HOURS` | Hours before approval times out | 24 |
| `PIPELINE_TIMEOUT_HOURS` | Max pipeline runtime | 48 |
| `DEFAULT_REPO` | Default repository | obtFusi/network-agent |

**Example Usage:**

```bash
# Start a pipeline
curl -X POST "http://localhost:8081/api/v1/pipelines/{id}/start"

# Check pending approvals
curl "http://localhost:8081/api/v1/approvals/pending"

# Approve a step
curl -X POST "http://localhost:8081/api/v1/approvals/{id}/approve" \
  -H "Content-Type: application/json" \
  -d '{"user": "admin", "comment": "LGTM"}'

# Abort a running pipeline
curl -X POST "http://localhost:8081/api/v1/pipelines/{id}/abort"
```

### 4.8 Development

```bash
cd infrastructure/cicd-dashboard

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest -v

# Run locally
uvicorn app.main:app --reload --port 8081
```

---

## 5. Local CI with act

### Installation

```bash
# Arch Linux
pacman -S act

# macOS
brew install act

# Or via Go
go install github.com/nektos/act@latest
```

### Configuration (`.actrc`)

```
--workflows=.github/workflows/ci.yml
```

Runs only the CI workflow, not Release/CodeQL (which require secrets/triggers).

### Usage

```bash
# Run all 4 jobs
act push

# Only one job
act push -j lint
act push -j docker

# With verbose output
act push -v
```

### What `act push` tests

| Job | Local Output |
|-----|--------------|
| lint | `ruff format --check .` + `ruff check` |
| test | `pytest` with coverage |
| security | `pip-audit` |
| docker | `docker build` + smoke test |

**Important:** Trivy runs with limitations in `act` (no action-specific features).

---

## 6. Branch Protection

### Required Status Checks

Configured under: Repository → Settings → Branches → `main`

| Check | Job | Must be green |
|-------|-----|---------------|
| lint | CI / lint | ✓ |
| test | CI / test | ✓ |
| security | CI / security | ✓ |
| docker | CI / docker | ✓ |

### Merge Rules

| Rule | Setting |
|------|---------|
| Require pull request | Yes |
| Require approvals | No (solo project) |
| Require status checks | Yes (4 jobs) |
| Require conversation resolution | No |
| Require linear history | No |
| Include administrators | Yes |

### Merge Strategy

```bash
# CORRECT: Waits for all checks
gh pr merge <N> --merge --delete-branch --auto

# WRONG: Bypasses Branch Protection!
gh pr merge <N> --admin  # NEVER!
```

---

## 7. Claude Code Integration

### Why Claude Code?

Network Agent was designed from the start for AI-assisted development:

1. **Skill-based Automation:** Recurring workflows as skills
2. **Evidence Required:** No merge claims without proof
3. **Consistency:** Skills ALWAYS execute all steps
4. **Error Prevention:** Skills don't forget steps

### Integration in CLAUDE.md

The project-specific `.claude/CLAUDE.md` defines:

```markdown
## SKILLS (Required when skill available!)

| Action | Skill | Invocation |
|--------|-------|------------|
| Create PR + merge | `/pr` | `Skill tool with skill: "pr"` |
| Create release/tag | `/release` | `Skill tool with skill: "release"` |
| Merge Dependabot PRs | `/merge-deps` | `Skill tool with skill: "merge-deps"` |
```

### Skill Triggers

| User says... | Claude does... |
|--------------|----------------|
| "create PR", "merge this" | `/pr` skill |
| "release", "new version", "create tag" | `/release` skill |
| "merge dependabot", "update deps" | `/merge-deps` skill |

---

## 8. Project-specific Skills

### 8.1 `/pr` - Pull Request Workflow

**Path:** `.claude/skills/pr/SKILL.md`
**Trigger:** "create PR", "merge this"

#### Workflow Steps

```
[1/6] Branch: feature/xyz       → Prepare Branch
[2/6] Local CI: lint, docker    → act push (MANDATORY)
[3/6] PR: .../pull/N            → Push & Create PR
[4/6] GitHub Actions: passed    → Wait for CI
[5/6] Issues: #N updated        → Update Issues
[6/6] Merged: main @ abc1234    → gh pr merge --auto
```

#### PR Body Template

```markdown
## Summary
- Change 1
- Change 2

## Test Plan
- [x] Local CI passed (lint, test, security, docker)
- [ ] Manual testing

Closes #N
```

#### Error Handling

- **Local CI red:** STOP, fix errors
- **GitHub Actions red:** STOP, fix locally, push
- **Never:** Skip steps, merge without green CI

### 8.2 `/release` - Release Workflow

**Path:** `.claude/skills/release/SKILL.md`
**Trigger:** "release", "new version", "create tag"

#### Input Formats

| Input | Result |
|-------|--------|
| `0.9.0` or `v0.9.0` | Version 0.9.0 |
| `patch` | 0.8.0 → 0.8.1 |
| `minor` | 0.8.0 → 0.9.0 |
| `major` | 0.8.0 → 1.0.0 |

#### Workflow Steps

```
[1/7] Version: 0.8.0 → 0.9.0    → Determine Version
[2/7] CHANGELOG: Entry exists   → Verify CHANGELOG (STOP if missing!)
[3/7] README Badge: Updated     → Update version badge
[4/7] cli.py: __version__       → Update SSOT
[5/7] Commit: abc1234           → Commit changes
[6/7] Tag: v0.9.0 pushed        → git tag + push
[7/7] Release: .../v0.9.0       → Verify GitHub Release
```

#### Prerequisites

- CHANGELOG.md MUST have entry for new version
- Entry MUST have Added, Changed, or Fixed section

### 8.3 `/merge-deps` - Dependabot Merge

**Path:** `.claude/skills/merge-deps/SKILL.md`
**Trigger:** "merge dependabot", "update deps"

#### Workflow

```
1. gh pr list --author "app/dependabot"
2. For each PR: gh pr checks <N>
3. Ready (✅) → gh pr merge --auto
4. Pending (⏳) → SKIP
5. Failed (❌) → SKIP, Report
6. git checkout main && git pull
```

#### Output Format

```
Dependabot PRs: 3 found

#6 actions/checkout v4 → v6
   Checks: ✅ lint, ✅ test, ✅ security, ✅ docker
   Status: MERGED

#7 github/codeql-action v3 → v4
   Checks: ❌ test (failed)
   Status: SKIPPED - CI failed

Summary: 1 merged, 1 skipped
Local main synced to abc1234
```

---

## 9. Global Skills

These skills are defined globally under `~/.claude/commands/` and available in ALL projects.

### 9.1 `/impl-plan` - Implementation Plan

**Path:** `~/.claude/commands/impl-plan.md`
**Purpose:** Detailed plan before complex implementations

#### When to use?

- New features with multiple files
- Refactorings with risk
- Security-relevant changes
- Any change that needs tests

#### Generated Sections

| Phase | Sections |
|-------|----------|
| 1: Analysis | Header, Blocking Questions, Prerequisites, TL;DR, Context, Glossary |
| 2: Planning | Quick Wins, Out of Scope, Dependencies, Risks, Security, Steps |
| 3: Config | Dependencies, Environment, Feature Flags, Tests, Acceptance Criteria |
| 4: Validation | Docs, Rollback, Cleanup, PR Checklist, DoD, TodoWrite Items |

#### Example Invocation

```
/impl-plan Add Web Search Tool with SearXNG
```

#### Special Features

- **Confidence Score:** 0-100% with reasoning
- **Risk Matrix:** Severity + Mitigation
- **Gherkin Specs:** Acceptance criteria as Given/When/Then
- **TodoWrite Items:** Automatic todo generation

### 9.2 `/claudemd` - CLAUDE.md Generator

**Path:** `~/.claude/commands/claudemd.md`
**Purpose:** Create optimal project-specific CLAUDE.md

#### When to use?

- New project starts
- Migrating existing project to Claude Code
- Updating CLAUDE.md rules

#### Generated Structure

```markdown
# CLAUDE CODE - [Project Name]

## SECTION 1: CRITICAL RULES (Stable - cached)
## SECTION 2: REQUIRED GUIDELINES (Stable - cached)
## SECTION 3: WORKFLOWS (Stable - cached)
---
## SECTION 4: PROJECT CONTEXT (Dynamic)
## SECTION 5: REFERENCES (Dynamic)
```

**Important:** Stable content FIRST for better prompt caching (90% cost reduction).

#### Analysis Phases

1. Detect project type (Web App, CLI, Library, ...)
2. Identify tech stack
3. Check existing structure
4. Capture team context

#### Known Parser Bugs (documented in skill)

| Bug | Workaround |
|-----|------------|
| #16700: Crash on empty lines after headers | No empty line after `#` |
| #16853: Path-scoped rules don't load | Test `/context` |
| #17085: System prompt override | Accept |

---

## 10. Workflow Diagrams

### Feature Development (End-to-End)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FEATURE DEVELOPMENT FLOW                            │
└─────────────────────────────────────────────────────────────────────────────┘

User: "Implement new feature X"
            │
            ▼
┌──────────────────────┐
│ 1. /impl-plan        │ ← Detailed planning
│    - Risk analysis   │
│    - Test strategy   │
│    - TodoWrite items │
└──────────────────────┘
            │
            ▼
┌──────────────────────┐
│ 2. Create issue      │
│    gh issue create   │
│    + status:backlog  │
└──────────────────────┘
            │
            ▼
┌──────────────────────┐
│ 3. Create branch     │
│    feature/name      │
└──────────────────────┘
            │
            ▼
┌──────────────────────┐
│ 4. Implementation    │ ← Write code
│    - Steps from      │
│      /impl-plan      │
│    - Check off todos │
└──────────────────────┘
            │
            ▼
┌──────────────────────┐
│ 5. act push          │ ← Local CI
│    ✓ lint            │
│    ✓ test            │
│    ✓ security        │
│    ✓ docker          │
└──────────────────────┘
            │
            ▼
┌──────────────────────┐
│ 6. Manual test       │ ← Collect evidence
│    docker run ...    │
│    → Screenshot/log  │
└──────────────────────┘
            │
            ▼
┌──────────────────────┐
│ 7. Documentation     │
│    - README          │
│    - CHANGELOG       │
│    - Version bump    │
└──────────────────────┘
            │
            ▼
┌──────────────────────┐
│ 8. /pr Skill         │ ← Automated:
│    - Push            │
│    - Create PR       │
│    - Wait for CI     │
│    - Merge           │
└──────────────────────┘
            │
            ▼
┌──────────────────────┐
│ 9. /release Skill    │ ← Optional for release
│    - Tag             │
│    - GitHub Release  │
└──────────────────────┘
```

### CI Pipeline (Job Dependencies)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CI PIPELINE                                    │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌──────────┐
                              │  PUSH    │
                              │  (main)  │
                              └────┬─────┘
                                   │
                                   ▼
                            ┌──────────────┐
                            │     lint     │ ← Format + Check + Bidi
                            │   (1 min)    │
                            └──────┬───────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              │
             ┌──────────┐   ┌──────────┐         │
             │   test   │   │ security │         │
             │  pytest  │   │ pip-audit│         │
             │ (1 min)  │   │ (30 sec) │         │
             └────┬─────┘   └────┬─────┘         │
                  │              │               │
                  └──────┬───────┘               │
                         │                       │
                         ▼                       │
                  ┌──────────────┐               │
                  │    docker    │ ◄─────────────┘
                  │ Build+Trivy  │
                  │   (3 min)    │
                  └──────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │   SUCCESS    │ → PR mergeable
                  └──────────────┘
```

---

## 11. Troubleshooting

### CI Fails

| Problem | Solution |
|---------|----------|
| `ruff format` failed | Run `ruff format .` locally |
| `ruff check` failed | Read errors in output and fix |
| `pytest` failed | Debug tests locally with `pytest -v` |
| `pip-audit` failed | Update dependency or open issue |
| `docker build` failed | Check Dockerfile, syntax errors |
| `trivy` CRITICAL | Base image CVE - often unfixable, wait |

### Merge Blocked

| Situation | Solution |
|-----------|----------|
| Checks pending | Use `--auto` flag (waits automatically) |
| Checks failed | Fix locally, push |
| Branch Protection | NEVER `--admin`, always `--auto` |

### Local CI vs Remote Different

| Possible Causes | Check |
|-----------------|-------|
| Python version | Local = 3.12, Remote = 3.12 |
| Dependencies | Compare `pip freeze` |
| Docker cache | `docker build --no-cache` |
| act version | Check `act --version` |

### Release Failed

| Problem | Solution |
|---------|----------|
| Tag already exists | Choose different version number |
| CHANGELOG missing | Add entry with correct format |
| Release action failed | Check manually under GitHub Releases |

---

## References

- **GitHub Actions Docs:** https://docs.github.com/en/actions
- **act (local CI):** https://github.com/nektos/act
- **Trivy Scanner:** https://aquasecurity.github.io/trivy/
- **CodeQL:** https://codeql.github.com/
- **Conventional Commits:** https://www.conventionalcommits.org/
- **Claude Code Docs:** https://docs.anthropic.com/en/docs/claude-code

---

*This documentation is SSOT for the CI/CD pipeline of the Network Agent project.*
