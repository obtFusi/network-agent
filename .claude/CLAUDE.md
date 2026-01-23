# NETWORK AGENT - DEVELOPMENT RULES

**Projekt:** KI-gesteuerter Netzwerk-Scanner | **Stack:** Python 3.12, Docker, nmap | **Sprache:** Deutsch

---

## TL;DR (Lies das IMMER zuerst!)
- **Skill-First:** `/pr`, `/release`, `/merge-deps` nutzen - NIEMALS manuell!
- **NIEMALS:** Direkt auf main, ohne Issue, ohne grüne CI, Secrets committen
- **IMMER:** Evidence liefern, Version bumpen, CHANGELOG updaten, User fragen vor Merge
- **SSOT:** `cli.py:__version__` ist die einzige Wahrheit für Versionsnummern
- **Public Project:** 40.000+ Downloads - alles muss 100% funktionieren

---

## Quick Reference
| Aktion | Command |
|--------|---------|
| **Lokale CI** | `act push` (alle 4 Jobs via .actrc) |
| **Docker Build** | `docker build -t network-agent:test .` |
| **Manueller Test** | `docker run -it --rm --network host -e LLM_API_KEY="$(jq -r '.["network-agent"].groq.api_key' ~/.claude/network-agent-credentials.json)" network-agent:test` |
| **Issue erstellen** | `gh issue create --title "[Type] Name" --label "type:feature,status:backlog"` |
| **Branch erstellen** | `git checkout main && git pull && git checkout -b feature/name` |
| **PR erstellen** | `gh pr create --title "feat: ..." --body "Closes #N"` |
| **PR Status** | `gh pr checks <number>` |
| **Merge** | `gh pr merge --merge --delete-branch` |
| **Kanban-View** | `for s in backlog ready in-progress review; do echo "=== $s ===" && gh issue list --label "status:$s"; done` |
| **Issue starten** | `gh issue edit <N> --remove-label "status:ready" --add-label "status:in-progress"` |
| **Issue ready** | `gh issue edit <N> --remove-label "status:backlog" --add-label "status:ready"` |
| **Appliance Build** | `gh workflow run appliance-build.yml -f version=X.Y.Z` |
| **Docker Image Push** | `gh workflow run docker-build.yml -f version=X.Y.Z` |
| **Runner Status** | `ssh root@github-runner systemctl status github-runner` |
| **Runner Logs** | `ssh root@github-runner journalctl -u github-runner -f` |

---

## CRITICAL RULES (NIEMALS verletzen!)

### NIEMALS (Hardcoded - keine Ausnahmen!)
```
NIEMALS manuell gh issue/pr create/merge - Skills verwenden!
NIEMALS direkt auf main committen
NIEMALS ohne Issue arbeiten
NIEMALS ohne grüne CI mergen
NIEMALS ohne Dokumentation mergen
NIEMALS ohne Version-Bump mergen
NIEMALS ohne User-OK mergen
NIEMALS Secrets in Code/Issues/PRs
NIEMALS "production ready" ohne Evidence
NIEMALS --admin Flag beim Merge (umgeht Branch Protection!)
```

### IMMER (Enforced - bei jeder Code-Änderung!)
```
IMMER erst prüfen ob Skill existiert (/pr, /release, /merge-deps)
IMMER Issue erstellen/referenzieren BEVOR Code geschrieben wird
IMMER Feature Branch erstellen (nicht main!)
IMMER lokale CI grün haben BEVOR Push
IMMER manuell testen (nicht nur bauen!)
IMMER Evidence dokumentieren (Command, Output, Scope, NOT Tested)
IMMER README aktualisieren bei User-sichtbaren Änderungen
IMMER CHANGELOG aktualisieren bei Features/Fixes
IMMER Version in cli.py erhöhen
IMMER User fragen vor Merge: "PR ist ready, soll ich mergen?"
```

---

## SKILLS (Pflicht bei verfügbarem Skill!)

**STOPP! Bevor du IRGENDETWAS manuell machst:**

| Aktion | Skill | Aufruf |
|--------|-------|--------|
| PR erstellen + mergen | `/pr` | `Skill tool mit skill: "pr"` |
| Release/Tag erstellen | `/release` | `Skill tool mit skill: "release"` |
| Dependabot PRs mergen | `/merge-deps` | `Skill tool mit skill: "merge-deps"` |

**Trigger-Phrasen:**
- "erstelle PR", "create PR", "merge this" → `/pr`
- "release", "neue version", "tag erstellen" → `/release`
- "merge dependabot", "update deps" → `/merge-deps`

**Warum Pflicht?** Skills enthalten den kompletten, getesteten Workflow. Manuelle Ausführung überspringt oft Schritte.

---

## WORKFLOW: Code-Änderung (Feature/Bugfix/Refactor)

**Gilt für JEDE Code-Änderung. Bei Fragen/Research: Normal arbeiten.**

### Phase 1: Vorbereitung
```
1.1 SKILL PRÜFEN
    └─ Existiert /pr Skill? → JA → SKILL VERWENDEN, nicht manuell!

1.2 ISSUE
    ├─ gh issue list --search "keyword"
    ├─ Gefunden? → Issue-Nummer notieren: #___
    └─ Nicht gefunden? → gh issue create --title "..." --label "enhancement|bug"
    ERGEBNIS: Issue #___ für diese Aufgabe

1.3 BRANCH
    ├─ git branch --show-current
    ├─ Auf main? → STOP! git checkout main && git pull && git checkout -b feature/name
    └─ Auf feature branch? → Weiter
    ERGEBNIS: Auf Branch feature/___ (nicht main!)
```

### Phase 2: Implementierung
```
2.1 CODE
    ├─ NUR das eine Issue #___ bearbeiten
    └─ Keine Scope-Erweiterung ohne neues Issue
    ERGEBNIS: Code-Änderungen fertig

2.2 LOKALE CI
    ├─ act push (alle Jobs: lint, test, security, docker)
    ├─ GRÜN? → Weiter
    └─ ROT? → Fehler fixen, zurück zu 2.2
    ERGEBNIS: Lokale CI GRÜN

2.3 DOCKER BUILD
    ├─ docker build -t network-agent:test .
    ├─ ERFOLG? → Weiter
    └─ FEHLER? → Fixen, zurück zu 2.2
    ERGEBNIS: Docker Image gebaut

2.4 MANUELLER TEST (KRITISCH - NICHT ÜBERSPRINGEN!)
    ├─ Container starten mit echten Credentials:
    │   docker run -it --rm --network host \
    │     -e LLM_API_KEY="$(jq -r '.["network-agent"].groq.api_key' ~/.claude/network-agent-credentials.json)" \
    │     -v /tmp/test-settings.yaml:/app/config/settings.yaml:ro \
    │     network-agent:test
    ├─ Feature WIRKLICH testen:
    │   ├─ CLI-Änderung? → Alle betroffenen Commands ausführen
    │   ├─ Scan-Änderung? → Echten Scan durchführen
    │   └─ Output-Änderung? → Output verifizieren
    ├─ FUNKTIONIERT? → Evidence sichern, weiter
    └─ FEHLER? → Fixen, zurück zu 2.2
    ERGEBNIS: Feature getestet, Evidence vorhanden
```

### Phase 3: Dokumentation
```
3.1 README
    ├─ User-sichtbare Änderung? (Command, Flag, Config, Output)
    │   ├─ JA → README.md aktualisieren
    │   └─ NEIN → Keine Änderung nötig
    ERGEBNIS: README aktuell

3.2 CHANGELOG
    ├─ IMMER bei Feature oder Bugfix!
    ├─ Version erhöhen (0.3.3 → 0.3.4)
    └─ Entry hinzufügen:
        ## [0.3.4] - YYYY-MM-DD
        ### Added/Fixed/Changed
        - **Name**: Beschreibung (#N)
    ERGEBNIS: CHANGELOG hat Entry

3.3 VERSION
    ├─ cli.py: __version__ = "0.3.4"
    └─ README.md Badge: version-0.3.4-blue
    ERGEBNIS: Version konsistent

3.4 COMMIT
    ├─ git add .
    └─ git commit -m "feat|fix: Beschreibung (closes #N)"
    ERGEBNIS: Commit erstellt
```

### Phase 4: Review & Merge
```
4.1 PUSH & PR
    ├─ git push -u origin feature/branch-name
    └─ gh pr create --title "feat: ..." --body "Closes #N"
    ERGEBNIS: PR #___ erstellt

4.2 GITHUB ACTIONS
    ├─ gh pr checks <PR-Nummer>
    ├─ GRÜN? → Weiter
    └─ ROT? → Lokal fixen, pushen, zurück zu 4.2
    ERGEBNIS: GitHub Actions GRÜN

4.3 USER-BESTÄTIGUNG (PFLICHT!)
    ├─ Checkliste zeigen:
    │   ┌─────────────────────────────────────────┐
    │   │ MERGE-CHECKLISTE für PR #___            │
    │   ├─────────────────────────────────────────┤
    │   │ [✓] Issue: #___                         │
    │   │ [✓] Branch: feature/___                 │
    │   │ [✓] Lokale CI: GRÜN                     │
    │   │ [✓] Docker Build: OK                    │
    │   │ [✓] Manuell getestet: JA                │
    │   │ [✓] README: Aktuell                     │
    │   │ [✓] CHANGELOG: Entry vorhanden          │
    │   │ [✓] Version: 0.3.x                      │
    │   │ [✓] GitHub Actions: GRÜN                │
    │   └─────────────────────────────────────────┘
    └─ Fragen: "PR ist ready. Soll ich mergen?"
    ERGEBNIS: User hat OK gegeben

4.4 MERGE
    ├─ gh pr merge <PR-Nummer> --merge --delete-branch
    ├─ Bei "Checks pending": --auto Flag nutzen (wartet automatisch)
    └─ NIEMALS --admin (umgeht Branch Protection!)
    ERGEBNIS: PR gemerged

4.5 CLEANUP
    ├─ git checkout main && git pull
    └─ Version-Bump dabei? → /release Skill für Tag
    ERGEBNIS: Fertig
```

---

## ISSUE-WORKFLOW (Kanban via CLI)

**Mindset:** Public Project mit 40.000+ Downloads - jedes Issue muss nachvollziehbar sein.

### Label-Schema
| Präfix | Labels | Zweck |
|--------|--------|-------|
| `status:` | backlog, ready, in-progress, review, blocked | Workflow-Status (Kanban-Spalten) |
| `type:` | feature, bug, docs, refactor, ci, deps | Klassifizierung |
| `priority:` | critical, high, medium, low | Priorisierung |

### Status-Zuweisung (WANN welcher Status?)
```
User sagt "mach X" / "do X"
    └─ Arbeit beginnt JETZT
    └─ → status:in-progress

User sagt "später X" / "plane X für später"
    └─ Kommt als nächstes dran
    └─ → status:ready

Agent schlägt Feature/Verbesserung vor
    └─ Vorschlag, nicht vom User beauftragt
    └─ → status:backlog

Während Planung: Thema zu umfangreich
    └─ In separates Issue auslagern
    └─ → status:backlog (neues Issue)

PR erstellt für Issue
    └─ Code in Review
    └─ → status:review

Blockiert durch externe Abhängigkeit
    └─ Kann nicht weiterarbeiten
    └─ → status:blocked
```

### Kanban-Befehle
```bash
# Alle Spalten anzeigen
for s in backlog ready in-progress review blocked; do
  echo "=== $s ===" && gh issue list --label "status:$s"
done

# Issue übernehmen (ready → in-progress)
gh issue edit <N> --remove-label "status:ready" --add-label "status:in-progress"

# Issue fertig zur Review
gh issue edit <N> --remove-label "status:in-progress" --add-label "status:review"

# Neues Issue mit korrekten Labels
gh issue create --title "[Feature] Name" \
  --label "type:feature,status:backlog,priority:medium"
```

### Conventional Commits (für PR-Titel)
```
feat:     Neues Feature
fix:      Bugfix
docs:     Dokumentation
refactor: Code-Refactoring
ci:       CI/CD Änderungen
deps:     Dependency Updates
```

---

## EVIDENCE-PFLICHT (Kein Merge ohne Beweis!)

**Bei Phase 2.4 (Manueller Test) MUSS dokumentiert werden:**

| Feld | Beschreibung |
|------|--------------|
| **Command** | Exakter Befehl der ausgeführt wurde |
| **Output** | Tatsächliche Ausgabe (redacted wenn sensibel) |
| **Scope** | Was wurde getestet |
| **NOT Tested** | Was wurde NICHT getestet (ehrlich!) |

**Beispiel:**
```
EVIDENCE:
- Command: docker run --rm network-agent:test python cli.py --version
- Output: Network Agent v0.3.4
- Scope: --version Flag funktioniert, Container startet
- NOT Tested: LLM-Kommunikation, Scan-Funktionalität, Session-Memory
```

**VERBOTEN ohne Evidence:**
- "Alles funktioniert"
- "Tests bestanden"
- "Production ready"
- Prozent-Angaben ohne Scope ("95% confident")

---

## SECRET-HYGIENE (Pentest-Tool = Hochsensible Daten!)

| VERBOTEN | ERLAUBT |
|----------|---------|
| API-Keys in Issues/PRs | Keys nur in .env (gitignored) |
| IPs/Hosts in PR-Beschreibung | Generische Beschreibung |
| Scan-Output in Logs | Redacted Output |
| Env-Vars in CI-Output | `set +x` vor sensitive commands |

**Checkliste vor jedem Commit:**
- [ ] Keine Secrets in Code/Commits
- [ ] .env in .gitignore
- [ ] Keine echten IPs in Tests/Docs (nur RFC 5737: 192.0.2.0/24)
- [ ] Credentials-File nicht committed

---

## VERSION-POLICY

**SSOT:** `cli.py:__version__`

| Änderungstyp | Version-Bump | Beispiel |
|--------------|--------------|----------|
| Breaking Change | MAJOR (1.0.0) | API-Änderung, Config-Format |
| Neues Feature | MINOR (0.4.0) | Neuer Command, neue Option |
| Bugfix | PATCH (0.3.4) | Fehlerkorrektur |
| Refactor (intern) | KEIN BUMP | Code-Cleanup ohne Verhaltensänderung |
| Docs-only | KEIN BUMP | README/CHANGELOG Updates |

**Synchronisation:**
1. `cli.py:__version__` ändern (SSOT)
2. `README.md` Badge aktualisieren
3. `CHANGELOG.md` Entry hinzufügen
4. Nach Merge: `/release` Skill für Git Tag

---

## CI/CD INFRASTRUKTUR

### Workflows und Trigger

| Workflow | Trigger | Zweck |
|----------|---------|-------|
| `ci.yml` | Push/PR auf main | Lint, Test, Security, Docker Smoke-Test |
| `codeql.yml` | Push/PR auf main | Security-Scan |
| `docker-build.yml` | Release published ODER manuell | Docker Image → ghcr.io |
| `appliance-build.yml` | Release published ODER manuell | VM Appliance qcow2 (Self-Hosted) |
| `release.yml` | Tag `v*` | GitHub Release aus CHANGELOG |

### Wann welcher Build läuft (Deterministische Regeln)

```
CODE-ÄNDERUNG (Python, Dockerfile, requirements.txt, etc.)
    └─ Push/PR → ci.yml läuft automatisch
    └─ Merge → KEIN automatischer Docker/Appliance Build
    └─ Grund: Änderungen sammeln, Release gebündelt

NEUER RELEASE GEWÜNSCHT
    └─ gh release create vX.Y.Z --generate-notes
    └─ → docker-build.yml läuft automatisch (Release Trigger)
    └─ → appliance-build.yml läuft automatisch (Release Trigger)
    └─ Grund: Beide Artefakte gehören zum Release

MANUELLER BUILD (Debugging, Test ohne Release)
    └─ Docker: gh workflow run docker-build.yml -f version=X.Y.Z
    └─ Appliance: gh workflow run appliance-build.yml -f version=X.Y.Z
```

### Release-Workflow (Reihenfolge beachten!)

```
1. Version in cli.py erhöhen (SSOT)
2. CHANGELOG.md Entry hinzufügen
3. README.md Badge aktualisieren
4. Commit + Push + PR + Merge
5. gh release create vX.Y.Z --generate-notes --title "vX.Y.Z"
   └─ Erstellt automatisch den Git Tag
   └─ Triggert docker-build.yml
   └─ Triggert appliance-build.yml
6. Warten auf beide Builds (~50 min für Appliance)
7. Release Assets werden automatisch hochgeladen
```

### CI Jobs (ci.yml)

| Job | Zweck |
|-----|-------|
| `lint` | ruff format + ruff check + Bidi-Check |
| `test` | pytest mit Coverage |
| `security` | pip-audit auf requirements.txt |
| `docker` | Build + Smoke-Test + Trivy-Scan |

**Branch Protection:** Alle 4 Jobs sind required checks.
**Merge-Flag:** `--auto` wartet auf alle Checks. NIEMALS `--admin`!

### Self-Hosted Runner (Appliance Build)

| Info | Wert |
|------|------|
| Runner | `github-runner` (Proxmox LXC Container) |
| Proxmox Host | `10.0.0.69` (für qm Befehle via SSH) |
| SSH Key | `/home/runner/.ssh/id_ed25519` auf Runner → Proxmox |
| Status | `ssh root@github-runner systemctl status github-runner` |
| Logs | `ssh root@github-runner journalctl -u github-runner -f` |
| Disk | 120GB, nach Build ~60GB frei (zstd + E2E Test) |
| RAM | 32GB (für Ollama Model Download) |
| Cleanup | `ssh root@github-runner fstrim -v /` (nach Build) |

**E2E Test Architektur:**
```
GitHub Runner (LXC) ──SSH──> Proxmox Host (10.0.0.69)
       │                            │
       │                            └─ qm create/start/destroy
       │                            └─ VM erstellen aus qcow2
       │
       └──SSH──> Test-VM (DHCP IP)
                     └─ Health Checks
                     └─ Docker Compose Status
```

**Appliance Build Phasen (4 separate Jobs):**
1. `validate` - Templates prüfen (ubuntu-latest, ~20s)
2. `build` - qcow2 bauen + komprimieren (self-hosted, ~40 min)
3. `e2e-test` - Test-VM + Health Checks (self-hosted, ~10 min)
4. `upload-release` - Zu Release hochladen (ubuntu-latest, ~5 min)

**Vorteil:** E2E-Fehler → nur Job 3 re-run (~10 min statt ~50 min)

---

## TOOL-VERWENDUNG

### Explore-Agent sparsam einsetzen!
**NICHT verwenden für:**
- Codebase verstehen (cli.py, tools/ direkt lesen!)
- Einzelne Dateien suchen (Glob/Read nutzen)

**NUR verwenden für:**
- Komplexe Suche über viele Dateien
- Unbekannte Codebase mit 100+ Dateien

**Explore-Agent kostet 50k+ Tokens und 1-2 Minuten!**

### Lokale Entwicklungsumgebung
```bash
source .venv/bin/activate   # NICHT /venv/bin/activate!
act push                    # Läuft alle 4 Jobs via .actrc
source .venv/bin/activate && ruff format . && ruff check .
```

---

## WICHTIGE DATEIEN

| Datei | Zweck | Wann ändern? |
|-------|-------|--------------|
| `cli.py` | CLI Entry Point + `__version__` | Bei jedem Release |
| `README.md` | User-Dokumentation | Bei User-sichtbaren Änderungen |
| `CHANGELOG.md` | Version History | Bei JEDEM Feature/Fix |
| `agent/core.py` | Agent Loop + Session Memory | Bei Agent-Logik |
| `agent/llm.py` | LLM Client | Bei API-Änderungen |
| `tools/network/ping_sweep.py` | nmap Integration | Bei Scan-Änderungen |
| `config/settings.yaml` | User-Konfiguration | Bei neuen Config-Optionen |

---

## TEST-SETUP

**Credentials:** `~/.claude/network-agent-credentials.json`
```json
{
  "network-agent": {
    "groq": { "api_key": "gsk_..." }
  }
}
```

**Test-Config:** `/tmp/test-settings.yaml`
```yaml
llm:
  provider:
    model: "llama-3.3-70b-versatile"
    base_url: "https://api.groq.com/openai/v1"
    temperature: 0.7
    max_tokens: 4096
```

---

## PLATTFORM-HINWEISE

| Plattform | LAN-Scan | Lösung |
|-----------|----------|--------|
| Linux | `--network host` | Direkt funktionsfähig |
| macOS | Docker Desktop VM | Host-nmap oder TCP-Connect |
| Windows | Docker Desktop VM | WSL2 oder Host-nmap |

---

## BEI PROBLEMEN

| Problem | Lösung |
|---------|--------|
| CI rot | Fehler lesen → lokal fixen → erneut pushen |
| Merge blockiert | `--auto` Flag (wartet auf Checks) |
| Test schlägt fehl | Bug fixen → zurück zu lokaler CI |
| README vergessen | Nachtragen → neuer Commit → Push |
| Version vergessen | Nachtragen → neuer Commit → Push |
| Issue vergessen | Nachträglich erstellen, Commit amenden |
