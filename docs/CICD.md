# CI/CD - Network Agent

**Letzte Aktualisierung:** 2026-01-23
**Status:** Production
**SSOT für:** CI/CD-Pipeline, Workflow-Automation, Claude Code Integration

---

## TL;DR

- **GitHub Actions:** 8 Workflows (CI, Release, CodeQL, Auto-Label, PR-Lint, Appliance-Build, Docker-Build, OVA-Build)
- **Lokale CI:** `act push` führt alle 4 Required Checks aus
- **Branch Protection:** 4 Required Status Checks (lint, test, security, docker)
- **Claude Code Skills:** `/pr`, `/release`, `/merge-deps` für automatisierte Workflows
- **Globale Skills:** `/claudemd`, `/impl-plan` für Planung und Projekt-Setup
- **Merge-Regel:** NIEMALS `--admin`, IMMER `--auto` (wartet auf Checks)

---

## Inhaltsverzeichnis

1. [Pipeline-Übersicht](#1-pipeline-übersicht)
2. [GitHub Actions Workflows](#2-github-actions-workflows)
3. [Lokale CI mit act](#3-lokale-ci-mit-act)
4. [Branch Protection](#4-branch-protection)
5. [Claude Code Integration](#5-claude-code-integration)
6. [Projekt-spezifische Skills](#6-projekt-spezifische-skills)
7. [Globale Skills](#7-globale-skills)
8. [Workflow-Diagramme](#8-workflow-diagramme)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Pipeline-Übersicht

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           NETWORK AGENT CI/CD                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  LOKAL (Entwickler)              GITHUB (Remote)           RELEASE         │
│  ┌──────────────────┐           ┌──────────────────┐      ┌─────────────┐  │
│  │ 1. Code schreiben│           │ 5. PR erstellen  │      │ 8. Tag push │  │
│  │ 2. act push      │──push──►  │ 6. CI läuft      │      │ 9. Release  │  │
│  │ 3. Docker build  │           │ 7. Merge (--auto)│──►   │    erstellt │  │
│  │ 4. Manuell testen│           └──────────────────┘      └─────────────┘  │
│  └──────────────────┘                                                       │
│         │                                │                                   │
│         ▼                                ▼                                   │
│  ┌──────────────────┐           ┌──────────────────┐                        │
│  │ /impl-plan       │           │ /pr Skill        │                        │
│  │ /claudemd        │           │ /release Skill   │                        │
│  │ (Planung)        │           │ /merge-deps      │                        │
│  └──────────────────┘           └──────────────────┘                        │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════   │
│  CLAUDE CODE INTEGRATION: Skills automatisieren jeden Schritt              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Architektur-Prinzipien

| Prinzip | Beschreibung |
|---------|--------------|
| **Fail Fast** | Lint vor Tests, Tests vor Security, alles vor Docker |
| **Required Checks** | 4 Jobs müssen grün sein bevor Merge möglich |
| **Lokal = Remote** | `act push` simuliert GitHub Actions exakt |
| **Skill-First** | Claude Code Skills statt manuelle CLI-Befehle |
| **Evidence-Pflicht** | Kein Merge ohne dokumentierte Tests |

---

## 2. GitHub Actions Workflows

### 2.1 CI Workflow (`.github/workflows/ci.yml`)

**Trigger:** Push und PR auf `main`
**Concurrency:** Nur ein Workflow pro Branch gleichzeitig

```yaml
jobs:
  lint:        # Ruff Format + Check + Bidi-Scan
  test:        # pytest mit Coverage (needs: lint)
  security:    # pip-audit auf requirements.txt (needs: lint)
  docker:      # Build + Smoke-Test + Trivy (needs: lint, test, security)
```

#### Job: lint

| Schritt | Beschreibung |
|---------|--------------|
| `ruff format --check .` | Code-Formatierung prüfen |
| `ruff check agent/ tools/ cli.py` | Linting (Fehler, Warnungen) |
| Bidi-Check | Unicode-Trojaner erkennen (CVE-2021-42574) |

**Bidi-Check Details:**
```bash
grep -rP '[\x{200B}-\x{200F}\x{202A}-\x{202E}\x{2066}-\x{2069}]' \
  --include='*.py' --include='*.yml' --include='*.yaml' \
  --include='*.md' --include='Dockerfile*' .
```

Scannt nach versteckten Unicode-Zeichen die Code-Injection ermöglichen könnten.

#### Job: test

```bash
pytest --cov=agent --cov=tools --cov-report=term-missing
```

Coverage für `agent/` und `tools/` Verzeichnisse.

#### Job: security

```bash
pip-audit -r requirements.txt
```

Prüft alle Dependencies auf bekannte Vulnerabilities.

#### Job: docker

| Schritt | Beschreibung |
|---------|--------------|
| `docker build -t network-agent:ci .` | Image bauen |
| `docker run --rm network-agent:ci python cli.py --version` | Smoke-Test |
| Trivy Scanner | Container-Vulnerabilities (CRITICAL, HIGH) |

**Trivy Konfiguration:**
```yaml
- uses: aquasecurity/trivy-action@0.28.0
  with:
    severity: 'CRITICAL,HIGH'
    ignore-unfixed: true  # Base-Image CVEs ohne Fix ignorieren
```

### 2.2 Release Workflow (`.github/workflows/release.yml`)

**Trigger:** Tag-Push (`v*`)
**Aktion:** Automatisches GitHub Release aus CHANGELOG

```yaml
steps:
  - Extract version from tag      # v0.8.0 → 0.8.0
  - Extract changelog for version # CHANGELOG.md parsen
  - Create GitHub Release         # softprops/action-gh-release@v2
```

**CHANGELOG-Parsing:**
```bash
awk "/^## \[${VERSION_NUM}\]/{flag=1; next} /^## \[/{flag=0} flag" CHANGELOG.md
```

Extrahiert den Abschnitt zwischen `## [X.Y.Z]` und dem nächsten `## [`.

### 2.3 CodeQL Workflow (`.github/workflows/codeql.yml`)

**Trigger:** Push, PR auf `main`, wöchentlich (Sonntag 00:00 UTC)
**Sprache:** Python
**Zweck:** Statische Code-Analyse für Security-Vulnerabilities

```yaml
- uses: github/codeql-action/init@v4
  with:
    languages: python
- uses: github/codeql-action/analyze@v4
```

### 2.4 Auto-Label Workflow (`.github/workflows/auto-label.yml`)

**Trigger:** Issue/PR erstellt

#### Issue-Labels (automatisch)

| Titel enthält | Labels |
|---------------|--------|
| `[bug]`, `bug:`, `fix:` | `type:bug`, `priority:high` |
| `[feature]`, `feat:` | `type:feature` |
| `[docs]`, `docs:` | `type:docs` |
| `[refactor]`, `refactor:` | `type:refactor` |
| `[ci]`, `ci:` | `type:ci` |

Alle Issues bekommen automatisch `status:backlog`.

#### PR-Labels (automatisch)

| Prefix | Label |
|--------|-------|
| `feat:`, `feat(` | `type:feature` |
| `fix:`, `fix(` | `type:bug` |
| `docs:`, `docs(` | `type:docs` |
| `deps:`, `chore(deps)` | `type:deps` |
| Autor `dependabot[bot]` | `type:deps` |

### 2.5 PR-Lint Workflow (`.github/workflows/pr-lint.yml`)

**Trigger:** PR opened, edited, synchronize
**Zweck:** Conventional Commits durchsetzen (soft enforcement)

```yaml
types: |
  feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert, deps
ignoreLabels: |
  type:deps  # Dependabot-PRs erlauben "Bump X from Y to Z"
```

**Wichtig:** NICHT als Required Check konfiguriert (Dependabot-Kompatibilität).

### 2.6 Appliance Build Workflow (Layered Architecture)

**Trigger:** `workflow_dispatch` (manuell) oder `release` (bei Tag)
**Runner:** Self-hosted (Proxmox LXC) für Build- und E2E-Jobs
**Artifact Storage:** MinIO (LAN) für schnellen Inter-Job Transfer

#### Layered Build System

Das Appliance-Build verwendet ein zweistufiges Layer-System:

```
┌─────────────────────────────────────────────────────────────────┐
│                    LAYERED BUILD ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  BASE IMAGE (monatlich, ~40 min)     LAYER (pro Release, ~10 min)│
│  ┌────────────────────────────┐     ┌────────────────────────┐  │
│  │ • Debian 13 (Trixie)       │     │ • /opt/network-agent/  │  │
│  │ • Docker CE                │     │ • docker-compose.yml   │  │
│  │ • systemd-networkd         │ ──► │ • Docker Images Pull   │  │
│  │ • SSH Hardening            │     │ • first-boot.sh        │  │
│  │ • Kernel Tuning            │     │ • Firewall Rules       │  │
│  │ • Ollama + Models (~20 GB) │     │ • VERSION file         │  │
│  └────────────────────────────┘     └────────────────────────┘  │
│           ↓                                   ↓                  │
│  appliance-base/base-2026-01.qcow2.zst   network-agent-0.10.1.qcow2│
│  (MinIO, persistent)                     (MinIO → GitHub Release) │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Vorteil:** Release-Builds dauern ~10 min statt ~50 min (Ollama bereits im Base Image)

#### Workflows

| Workflow | Trigger | Frequenz | Dauer | Output |
|----------|---------|----------|-------|--------|
| `base-appliance.yml` | Manuell / Cron (1. des Monats) | Monatlich | ~40 min | `appliance-base/` bucket |
| `appliance-build.yml` | Release / Manuell | Pro Release | ~15 min | GitHub Release |

```yaml
# Base Image bauen (monatlich)
gh workflow run base-appliance.yml -f base_version=2026-01

# Layer Build (pro Release)
gh workflow run appliance-build.yml -f version=0.10.1 -f base_version=latest
```

**Jobs (appliance-build.yml, 3 jobs, MinIO for fast transfer):**

| Job | Runner | Timeout | Description |
|-----|--------|---------|-------------|
| `validate` | ubuntu-latest | 10m | Validate Packer templates + docker-compose |
| `build` | **self-hosted** | 30m | Download base, build layer, upload to MinIO |
| `e2e-test` | **self-hosted** | 30m | Download from MinIO, test VM, upload to Release |

**Job Dependencies:**
```
validate → build → e2e-test
              ↓         ↓
         (downloads   (on release: upload
          base from    to GitHub Release)
          MinIO)
```

**MinIO Artifact Storage:**

| Aspekt | Wert |
|--------|------|
| Server | 10.0.0.165:9000 (Proxmox LXC 160) |
| Buckets | `appliance-base` (persistent), `appliance-builds` (temp) |
| Retention | Keine - Cleanup nach E2E-Job |
| Transfer Speed | ~100 MB/s (LAN) vs ~5 MB/s (GitHub Artifacts) |

**Bucket-Struktur:**
```
appliance-base/              # Persistent (manuelles Cleanup)
  ├── base-2026-01.qcow2.zst
  ├── base-latest.qcow2.zst  # Symlink to latest
  └── SHA256SUMS-2026-01

appliance-builds/            # Temporary (auto-cleanup nach E2E)
  └── 0.10.1/
      ├── *.part-*
      ├── SHA256SUMS
      └── install-network-agent.sh
```

**Secrets:**
- `MINIO_ENDPOINT` - MinIO Server URL
- `MINIO_ACCESS_KEY` - Access Key
- `MINIO_SECRET_KEY` - Secret Key

**Benefits:**
- Layered Build: ~10 min statt ~50 min pro Release
- Inter-Job Transfer: 5 min statt 75 min (15x schneller)
- E2E failure: Re-run only `e2e-test` (~10 min)
- Release Upload: Direkt vom E2E-Job nach erfolgreichem Test
- Re-run command: `gh run rerun <run-id> --job e2e-test`

**Why Self-hosted + MinIO?**
- GitHub-hosted runners only have ~14GB disk (image is 30GB+)
- Packer requires KVM/QEMU (not available on GitHub-hosted)
- Build requires ~32GB RAM for Ollama model download
- GitHub Artifact upload rate-limited to ~5 MB/s (27GB = 75 min)

### 2.7 Docker Build Workflow (`.github/workflows/docker-build.yml`)

**Trigger:** Push auf `main` (bei Änderungen an Dockerfile, Code, Config) oder `workflow_dispatch`
**Zweck:** Docker Image zu ghcr.io pushen

```yaml
# Manuell triggern mit Version
gh workflow run docker-build.yml -f version=0.9.0
```

**Schritte:**

| Schritt | Beschreibung |
|---------|--------------|
| Login to ghcr.io | Mit GITHUB_TOKEN authentifizieren |
| Extract metadata | Version aus cli.py oder Input |
| Build and push | Multi-Tag: `version` + `latest` |

**Tags:**
- `ghcr.io/obtfusi/network-agent:0.9.0`
- `ghcr.io/obtfusi/network-agent:latest`

### 2.8 Self-hosted Runner

**Location:** Proxmox LXC 150 (`github-runner`)
**Host:** 10.0.0.69 (Proxmox)

| Ressource | Wert |
|-----------|------|
| OS | Debian 13 |
| RAM | 32 GB |
| CPU | 8 Cores |
| Disk | 120 GB |
| Labels | `self-hosted`, `Linux`, `X64`, `ova-builder` |

**Security (Public Repo!):**
- **Ephemeral Mode:** Runner re-registriert nach jedem Job
- **Trigger-Restriction:** NUR `workflow_dispatch` + `release`, NIEMALS `pull_request`
- **Dedicated User:** Läuft als `runner`, nicht als root
- **PAT in .env:** Token nicht im systemd-Service gespeichert

**Management:**

```bash
# Runner Status prüfen
ssh root@github-runner systemctl status github-runner

# Logs anzeigen
ssh root@github-runner journalctl -u github-runner -f

# Runner in GitHub prüfen
gh api /repos/obtFusi/network-agent/actions/runners --jq '.runners[]'
```

**Scripts:**
- `infrastructure/scripts/create-runner-lxc.sh` - LXC Setup auf Proxmox
- `infrastructure/scripts/runner-wrapper.sh` - Ephemeral Loop mit Token-Refresh

### 2.9 MinIO Artifact Storage

**Location:** Proxmox LXC 160 (`minio`)
**IP:** 10.0.0.165
**Ports:** 9000 (API), 9001 (Console)

| Ressource | Wert |
|-----------|------|
| OS | Debian 12 |
| RAM | 2 GB |
| CPU | 2 Cores |
| Disk | 50 GB |
| Buckets | `appliance-base` (persistent), `appliance-builds` (temp) |
| Retention | Keine (Cleanup nach E2E-Job)

**Warum MinIO statt GitHub Artifacts?**

| Aspekt | GitHub Artifacts | MinIO |
|--------|------------------|-------|
| Upload Speed | ~5 MB/s (Rate-Limited) | ~100 MB/s (LAN) |
| 27 GB Upload | ~75 min | ~5 min |
| Kosten | Gratis (2 GB limit) | Gratis (self-hosted) |
| Kontrolle | GitHub managed | Selbst verwaltet |

**Management:**

```bash
# MinIO Status prüfen
ssh root@10.0.0.69 "pct exec 160 -- systemctl status minio"

# Bucket-Inhalt anzeigen
ssh root@10.0.0.69 "pct exec 160 -- /usr/local/bin/mc ls local/appliance-builds/"

# Manuelles Cleanup
ssh root@10.0.0.69 "pct exec 160 -- /usr/local/bin/mc rm --recursive --force local/appliance-builds/OLD_VERSION/"

# Console (Web UI)
# http://10.0.0.165:9001 (minioadmin / [siehe Secrets])
```

**Troubleshooting:**

| Problem | Lösung |
|---------|--------|
| MinIO nicht erreichbar | `pct start 160` auf Proxmox |
| Upload fehlschlägt | Secrets prüfen, Netzwerk testen |
| Bucket voll | `mc rm --recursive minio/appliance-builds/OLD_VERSION/` |
| appliance-base voll | Alte Base-Images manuell löschen |
| Credentials vergessen | `ssh root@10.0.0.69 "pct exec 160 -- cat /etc/minio.env"` |

---

## 3. Lokale CI mit act

### Installation

```bash
# Arch Linux
pacman -S act

# macOS
brew install act

# Oder via Go
go install github.com/nektos/act@latest
```

### Konfiguration (`.actrc`)

```
--workflows=.github/workflows/ci.yml
```

Führt nur den CI-Workflow aus, nicht Release/CodeQL (die benötigen Secrets/Triggers).

### Verwendung

```bash
# Alle 4 Jobs ausführen
act push

# Nur einen Job
act push -j lint
act push -j docker

# Mit Verbose-Output
act push -v
```

### Was `act push` testet

| Job | Lokaler Output |
|-----|----------------|
| lint | `ruff format --check .` + `ruff check` |
| test | `pytest` mit Coverage |
| security | `pip-audit` |
| docker | `docker build` + Smoke-Test |

**Wichtig:** Trivy läuft bei `act` nur eingeschränkt (keine Action-spezifischen Features).

---

## 4. Branch Protection

### Required Status Checks

Konfiguriert unter: Repository → Settings → Branches → `main`

| Check | Job | Muss grün sein |
|-------|-----|----------------|
| lint | CI / lint | ✓ |
| test | CI / test | ✓ |
| security | CI / security | ✓ |
| docker | CI / docker | ✓ |

### Merge-Regeln

| Regel | Einstellung |
|-------|-------------|
| Require pull request | Ja |
| Require approvals | Nein (Solo-Projekt) |
| Require status checks | Ja (4 Jobs) |
| Require conversation resolution | Nein |
| Require linear history | Nein |
| Include administrators | Ja |

### Merge-Strategie

```bash
# RICHTIG: Wartet auf alle Checks
gh pr merge <N> --merge --delete-branch --auto

# FALSCH: Umgeht Branch Protection!
gh pr merge <N> --admin  # NIEMALS!
```

---

## 5. Claude Code Integration

### Warum Claude Code?

Network Agent wurde von Anfang an für KI-gestützte Entwicklung konzipiert:

1. **Skill-basierte Automation:** Wiederkehrende Workflows als Skills
2. **Evidence-Pflicht:** Keine Merge-Claims ohne Beweis
3. **Konsistenz:** Skills führen IMMER alle Schritte aus
4. **Fehler-Prävention:** Skills vergessen keine Schritte

### Integration in CLAUDE.md

Die projektspezifische `.claude/CLAUDE.md` definiert:

```markdown
## SKILLS (Pflicht bei verfügbarem Skill!)

| Aktion | Skill | Aufruf |
|--------|-------|--------|
| PR erstellen + mergen | `/pr` | `Skill tool mit skill: "pr"` |
| Release/Tag erstellen | `/release` | `Skill tool mit skill: "release"` |
| Dependabot PRs mergen | `/merge-deps` | `Skill tool mit skill: "merge-deps"` |
```

### Skill-Trigger

| User sagt... | Claude tut... |
|--------------|---------------|
| "erstelle PR", "create PR", "merge this" | `/pr` Skill |
| "release", "neue version", "tag erstellen" | `/release` Skill |
| "merge dependabot", "update deps" | `/merge-deps` Skill |

---

## 6. Projekt-spezifische Skills

### 6.1 `/pr` - Pull Request Workflow

**Pfad:** `.claude/skills/pr/SKILL.md`
**Trigger:** "erstelle PR", "create PR", "merge this"

#### Workflow-Schritte

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

- **Lokale CI rot:** STOP, Fehler fixen
- **GitHub Actions rot:** STOP, lokal fixen, push
- **Nie:** Skip steps, merge ohne grüne CI

### 6.2 `/release` - Release Workflow

**Pfad:** `.claude/skills/release/SKILL.md`
**Trigger:** "release", "neue version", "tag erstellen"

#### Input-Formate

| Eingabe | Ergebnis |
|---------|----------|
| `0.9.0` oder `v0.9.0` | Version 0.9.0 |
| `patch` | 0.8.0 → 0.8.1 |
| `minor` | 0.8.0 → 0.9.0 |
| `major` | 0.8.0 → 1.0.0 |

#### Workflow-Schritte

```
[1/7] Version: 0.8.0 → 0.9.0    → Determine Version
[2/7] CHANGELOG: Entry exists   → Verify CHANGELOG (STOP if missing!)
[3/7] README Badge: Updated     → Update version badge
[4/7] cli.py: __version__       → Update SSOT
[5/7] Commit: abc1234           → Commit changes
[6/7] Tag: v0.9.0 pushed        → git tag + push
[7/7] Release: .../v0.9.0       → Verify GitHub Release
```

#### Voraussetzungen

- CHANGELOG.md MUSS Entry für neue Version haben
- Entry MUSS Added, Changed, oder Fixed Section haben

### 6.3 `/merge-deps` - Dependabot Merge

**Pfad:** `.claude/skills/merge-deps/SKILL.md`
**Trigger:** "merge dependabot", "update deps"

#### Workflow

```
1. gh pr list --author "app/dependabot"
2. Für jeden PR: gh pr checks <N>
3. Ready (✅) → gh pr merge --auto
4. Pending (⏳) → SKIP
5. Failed (❌) → SKIP, Report
6. git checkout main && git pull
```

#### Output-Format

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

## 7. Globale Skills

Diese Skills sind global unter `~/.claude/commands/` definiert und in ALLEN Projekten verfügbar.

### 7.1 `/impl-plan` - Implementierungsplan

**Pfad:** `~/.claude/commands/impl-plan.md`
**Zweck:** Detaillierter Plan vor komplexen Implementierungen

#### Wann verwenden?

- Neue Features mit mehreren Dateien
- Refactorings mit Risiko
- Sicherheitsrelevante Änderungen
- Jede Änderung die Tests braucht

#### Generierte Sektionen

| Phase | Sektionen |
|-------|-----------|
| 1: Analyse | Header, Blocking Questions, Prerequisites, TL;DR, Kontext, Glossar |
| 2: Planung | Quick Wins, Nicht im Scope, Abhängigkeiten, Risiken, Security, Steps |
| 3: Config | Dependencies, Environment, Feature Flags, Tests, Acceptance Criteria |
| 4: Validierung | Docs, Rollback, Cleanup, PR Checkliste, DoD, TodoWrite Items |

#### Beispiel-Aufruf

```
/impl-plan Füge Web Search Tool mit SearXNG hinzu
```

#### Besondere Merkmale

- **Confidence Score:** 0-100% mit Begründung
- **Risiko-Matrix:** Schwere + Mitigation
- **Gherkin-Specs:** Akzeptanzkriterien als Given/When/Then
- **TodoWrite-Items:** Automatische Todo-Generierung

### 7.2 `/claudemd` - CLAUDE.md Generator

**Pfad:** `~/.claude/commands/claudemd.md`
**Zweck:** Optimale projektspezifische CLAUDE.md erstellen

#### Wann verwenden?

- Neues Projekt startet
- Bestehendes Projekt zu Claude Code migrieren
- CLAUDE.md-Regeln aktualisieren

#### Generierte Struktur

```markdown
# CLAUDE CODE - [Projektname]

## SECTION 1: CRITICAL RULES (Stabil - wird gecached)
## SECTION 2: REQUIRED GUIDELINES (Stabil - wird gecached)
## SECTION 3: WORKFLOWS (Stabil - wird gecached)
---
## SECTION 4: PROJECT CONTEXT (Dynamisch)
## SECTION 5: REFERENCES (Dynamisch)
```

**Wichtig:** Stabile Inhalte ZUERST für besseres Prompt Caching (90% Kostenreduktion).

#### Analyse-Phasen

1. Projekt-Typ erkennen (Web App, CLI, Library, ...)
2. Tech-Stack identifizieren
3. Bestehende Struktur prüfen
4. Team-Kontext erfassen

#### Bekannte Parser-Bugs (im Skill dokumentiert)

| Bug | Workaround |
|-----|------------|
| #16700: Crash bei Leerzeilen nach Headers | Keine Leerzeile nach `#` |
| #16853: Path-scoped Rules laden nicht | `/context` testen |
| #17085: System Prompt Override | Akzeptieren |

---

## 8. Workflow-Diagramme

### Feature-Entwicklung (End-to-End)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FEATURE DEVELOPMENT FLOW                            │
└─────────────────────────────────────────────────────────────────────────────┘

User: "Implementiere neues Feature X"
            │
            ▼
┌──────────────────────┐
│ 1. /impl-plan        │ ← Detaillierte Planung
│    - Risiko-Analyse  │
│    - Test-Strategie  │
│    - TodoWrite Items │
└──────────────────────┘
            │
            ▼
┌──────────────────────┐
│ 2. Issue erstellen   │
│    gh issue create   │
│    + status:backlog  │
└──────────────────────┘
            │
            ▼
┌──────────────────────┐
│ 3. Branch erstellen  │
│    feature/name      │
└──────────────────────┘
            │
            ▼
┌──────────────────────┐
│ 4. Implementierung   │ ← Code schreiben
│    - Schritte aus    │
│      /impl-plan      │
│    - Todos abhaken   │
└──────────────────────┘
            │
            ▼
┌──────────────────────┐
│ 5. act push          │ ← Lokale CI
│    ✓ lint            │
│    ✓ test            │
│    ✓ security        │
│    ✓ docker          │
└──────────────────────┘
            │
            ▼
┌──────────────────────┐
│ 6. Manueller Test    │ ← Evidence sammeln
│    docker run ...    │
│    → Screenshot/Log  │
└──────────────────────┘
            │
            ▼
┌──────────────────────┐
│ 7. Dokumentation     │
│    - README          │
│    - CHANGELOG       │
│    - Version bump    │
└──────────────────────┘
            │
            ▼
┌──────────────────────┐
│ 8. /pr Skill         │ ← Automatisiert:
│    - Push            │
│    - PR erstellen    │
│    - CI warten       │
│    - Merge           │
└──────────────────────┘
            │
            ▼
┌──────────────────────┐
│ 9. /release Skill    │ ← Optional bei Release
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

## 9. Troubleshooting

### CI schlägt fehl

| Problem | Lösung |
|---------|--------|
| `ruff format` failed | `ruff format .` lokal ausführen |
| `ruff check` failed | Fehler in Output lesen und fixen |
| `pytest` failed | Tests lokal mit `pytest -v` debuggen |
| `pip-audit` failed | Dependency updaten oder Issue öffnen |
| `docker build` failed | Dockerfile prüfen, Syntax-Fehler |
| `trivy` CRITICAL | Base-Image CVE - oft nicht fixbar, warten |

### Merge blockiert

| Situation | Lösung |
|-----------|--------|
| Checks pending | `--auto` Flag nutzt (wartet automatisch) |
| Checks failed | Lokal fixen, pushen |
| Branch Protection | NIE `--admin`, immer `--auto` |

### Lokale CI vs Remote unterschiedlich

| Mögliche Ursachen | Prüfen |
|-------------------|--------|
| Python-Version | Local = 3.12, Remote = 3.12 |
| Dependencies | `pip freeze` vergleichen |
| Docker Cache | `docker build --no-cache` |
| act-Version | `act --version` prüfen |

### Release fehlgeschlagen

| Problem | Lösung |
|---------|--------|
| Tag existiert schon | Anderer Version-Nummer wählen |
| CHANGELOG fehlt | Entry hinzufügen mit korrektem Format |
| Release-Action failed | Manuell unter GitHub Releases prüfen |

---

## Referenzen

- **GitHub Actions Docs:** https://docs.github.com/en/actions
- **act (lokale CI):** https://github.com/nektos/act
- **Trivy Scanner:** https://aquasecurity.github.io/trivy/
- **CodeQL:** https://codeql.github.com/
- **Conventional Commits:** https://www.conventionalcommits.org/
- **Claude Code Docs:** https://docs.anthropic.com/en/docs/claude-code

---

*Diese Dokumentation ist SSOT für die CI/CD-Pipeline des Network Agent Projekts.*
