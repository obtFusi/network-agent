# Network Agent

[![Version](https://img.shields.io/badge/version-0.9.0-blue.svg)](CHANGELOG.md)

> **Für Entwickler:** [CI/CD-Dokumentation](docs/CICD.md) - Pipeline, GitHub Actions, Claude Code Skills

Ein KI-gesteuerter Netzwerk-Scanner. Statt komplizierte Terminal-Befehle zu lernen, stellst du einfach Fragen wie *"Welche Geräte sind in meinem Netzwerk?"* - der Agent erledigt den Rest.

## Breaking Change in v0.7.0

> **Ab Version 0.7.0** sind alle CLI-Meldungen und der System-Prompt auf Englisch umgestellt.
>
> **Warum?** Das Projekt ist auf GitHub öffentlich und soll international nutzbar sein.
>
> **Du willst deutsche Antworten?** Füge am Ende von `config/prompts/system.md` hinzu:
> ```
> Always respond in German (Deutsch).
> ```

## Was macht dieses Tool?

Der Network Agent kombiniert:
- **Natürliche Sprache**: Du fragst auf Deutsch, was du wissen willst
- **KI-Verarbeitung**: Jede OpenAI-kompatible API versteht deine Anfrage
- **Netzwerk-Tools**: nmap führt den eigentlichen Scan durch
- **Verständliche Antworten**: Die Ergebnisse werden für dich aufbereitet

**Beispiel:**
```
> Welche Geräte sind im Netzwerk 192.168.1.0/24 online?

Ich habe 7 aktive Geräte gefunden:
- 192.168.1.1 (Router)
- 192.168.1.10 (Desktop-PC)
- 192.168.1.15 (Smartphone)
...
```

## Unterstützte LLM Provider

Network Agent funktioniert mit jeder **OpenAI-kompatiblen API**. Das bedeutet:

| Provider | API Endpoint | Beispiel Models |
|----------|-------------|-----------------|
| [OpenAI](https://openai.com) | `https://api.openai.com/v1` | gpt-4, gpt-3.5-turbo |
| [Venice.ai](https://venice.ai) | `https://api.venice.ai/api/v1` | llama-3.3-70b, mistral-large |
| [Together.ai](https://together.ai) | `https://api.together.xyz/v1` | llama-3-70b, mixtral-8x7b |
| [Groq](https://groq.com) | `https://api.groq.com/openai/v1` | llama-3.3-70b, mixtral-8x7b |
| [Ollama](https://ollama.com) | `http://localhost:11434/v1` | llama3, mistral, codellama |
| [LM Studio](https://lmstudio.ai) | `http://localhost:1234/v1` | Beliebige lokale Models |

**Voraussetzung:** Der Provider muss die [OpenAI Chat Completions API](https://platform.openai.com/docs/api-reference/chat) mit Tool/Function Calling unterstützen.

## Voraussetzungen

1. **Docker** - [Download Docker Desktop](https://www.docker.com/products/docker-desktop/)
2. **API Key** von einem unterstützten Provider (siehe oben)
3. **Git** (optional) - [Download Git](https://git-scm.com/downloads)

## Installation

### 1. Repository herunterladen

```bash
git clone https://github.com/obtFusi/network-agent.git
cd network-agent
```

Oder: [ZIP herunterladen](https://github.com/obtFusi/network-agent/archive/refs/heads/main.zip) und entpacken.

### 2. LLM Provider konfigurieren

**Schritt A: API Key setzen**

Kopiere die Vorlage und trage deinen API Key ein:

```bash
cp .env.example .env
```

Bearbeite `.env`:
```
LLM_API_KEY=dein_api_key_hier
```

**Schritt B: Provider und Model konfigurieren**

Bearbeite `config/settings.yaml`:

```yaml
llm:
  provider:
    model: "gpt-4"                        # <-- Dein Model
    base_url: "https://api.openai.com/v1" # <-- Deine API URL
    temperature: 0.7
    max_tokens: 4096
```

<details>
<summary><strong>Beispiel-Konfigurationen für verschiedene Provider</strong></summary>

**OpenAI:**
```yaml
model: "gpt-4"
base_url: "https://api.openai.com/v1"
```

**Venice.ai:**
```yaml
model: "llama-3.3-70b"
base_url: "https://api.venice.ai/api/v1"
```

**Groq (schnell & günstig):**
```yaml
model: "llama-3.3-70b-versatile"
base_url: "https://api.groq.com/openai/v1"
```

**Ollama (lokal):**
```yaml
model: "llama3"
base_url: "http://host.docker.internal:11434/v1"
```
*Hinweis: `host.docker.internal` erlaubt Docker den Zugriff auf Host-Services*

</details>

<details>
<summary><strong>Scan-Einstellungen anpassen (Optional)</strong></summary>

**Bestimmte Geräte vom Scan ausschließen:**

Du willst bestimmte IPs nicht scannen (z.B. kritische Server, Drucker)? Füge sie in `config/settings.yaml` hinzu:

```yaml
scan:
  exclude_ips:
    - "192.168.1.1"       # Router nicht scannen
    - "192.168.1.100"     # NAS ausschließen
    - "10.0.0.0/24"       # Ganzes Management-Netz ignorieren
```

**Scan-Timeout erhöhen:**

Bei langsamen Netzwerken oder vielen Hosts kann der Scan abbrechen. Erhöhe das Timeout:

```yaml
scan:
  timeout: 300  # 5 Minuten statt Standard 2 Minuten
```

**Größere Netzwerke scannen:**

Standardmäßig sind Port-Scans auf /24 (256 Hosts) begrenzt. Für größere Netze:

```yaml
scan:
  max_hosts_portscan: 1024  # Erlaubt /22 Netzwerke
```

*Hinweis: Größere Scans dauern entsprechend länger!*

</details>

### 3. Docker Image erstellen

```bash
docker build -t network-agent:latest .
```

### 4. Agent starten

**Mit Web-Suche (empfohlen):**

```bash
# Linux (LAN-Scans + Web-Suche):
docker compose up

# macOS/Windows (Web-Suche, eingeschränkte Netzwerk-Scans):
docker compose -f docker-compose.macos.yml up
```

**Ohne Web-Suche (wie bisher):**

```bash
# Linux:
docker run -it --rm --network host --env-file .env network-agent:latest

# Windows mit WSL2:
docker run -it --rm --network host --env-file .env network-agent:latest

# Windows ohne WSL / macOS:
docker run -it --rm --env-file .env network-agent:latest
```

> **Hinweis:** Docker Compose startet automatisch SearXNG für Web-Suchen. Ohne `--network host` ist der LAN-Scan eingeschränkt.

### Alternative: Proxmox Appliance

Für eine schlüsselfertige Lösung gibt es eine vorkonfigurierte **Proxmox VM** mit allem vorinstalliert:

<details>
<summary><strong>One-Click Installation auf Proxmox</strong></summary>

**Was ist enthalten?**
- Network Agent (vorinstalliert)
- Ollama mit Qwen3 30B-A3B (20GB lokales LLM, kein API-Key nötig)
- Caddy Reverse Proxy (HTTPS + Basic Auth)
- PostgreSQL (Datenbank)
- Offline-fähig (keine externen Dependencies zur Laufzeit)

**Systemanforderungen:**
- 24-32 GB RAM (LLM benötigt ~20 GB)
- 4-8 CPU Cores
- 100 GB Disk
- Proxmox VE 8.x

**Installation (One-Click):**

```bash
# Auf dem Proxmox-Host ausführen:
curl -sSL https://github.com/obtFusi/network-agent/releases/latest/download/install-network-agent.sh | bash -s -- 200

# Oder mit benutzerdefiniertem Storage:
curl -sSL ... | bash -s -- 200 ceph-pool
```

Das Script:
1. Lädt das Image (~8GB komprimiert)
2. Verifiziert SHA256 Checksums
3. Dekomprimiert zu ~22GB qcow2
4. Erstellt VM 200 mit optimalen Einstellungen
5. Ready to start!

**Manueller Download:**

```bash
# Parts herunterladen
wget https://github.com/obtFusi/network-agent/releases/latest/download/network-agent-0.4.0.qcow2.zst.part-aa
wget https://github.com/obtFusi/network-agent/releases/latest/download/network-agent-0.4.0.qcow2.zst.part-ab
# ... (5 Parts total)

# Zusammenfügen und dekomprimieren
cat network-agent-*.part-* | zstd -d -o network-agent.qcow2

# VM erstellen
qm create 200 --name network-agent --memory 32768 --cores 8 --cpu host
qm importdisk 200 network-agent.qcow2 local-lvm --format qcow2
qm set 200 --scsi0 local-lvm:vm-200-disk-0 --boot order=scsi0
```

**Erster Start:**

```bash
qm start 200
qm terminal 200
```

Beim ersten Login:
1. Neues Root-Passwort setzen (Pflicht!)
2. Web-Credentials werden generiert und angezeigt
3. Services starten automatisch

**Zugriff:**
- Web UI: `https://<VM-IP>` (Credentials aus First-Boot)
- SSH: `ssh root@<VM-IP>`

**Scan-Modus (Host-Network für L2/L3):**

```bash
ssh root@<VM-IP>
cd /opt/network-agent
docker compose down
docker compose -f docker-compose.yml -f docker-compose.scan-mode.yml up -d
```

**Ports:**
- 443: HTTPS Web Interface (Caddy)
- 22: SSH

</details>

## Verwendung

Nach dem Start siehst du:
```
Network Agent starting...
   Model: gpt-4
   Context limit: 8,192 tokens
   Type /help for available commands

>
```

### Was kann ich fragen?

**Geräte im Netzwerk finden:**
- `Welche Geräte sind im Netzwerk 192.168.1.0/24?`
- `Scanne mein Heimnetzwerk 192.168.178.0/24`
- `Wer ist gerade online?` *(wenn du vorher ein Netzwerk gescannt hast)*
- `Zeig mir alle aktiven Hosts in 10.0.0.0/24`

**DNS-Abfragen:**
- `Welche IP hat example.com?`
- `Zeig mir die MX-Records von gmail.com`
- `Reverse DNS für 8.8.8.8`
- `Welcher Nameserver ist für heise.de zuständig?`

> **Gut zu wissen:**
> - MX = Mailserver, NS = Nameserver, TXT = Texteinträge (z.B. SPF)
> - "Reverse DNS" findet den Hostnamen zu einer IP-Adresse
> - DNS-Abfragen funktionieren auch für öffentliche Domains

**Port-Scans:**
- `Scanne die Ports 22, 80, 443 auf 192.168.1.1`
- `Welche Ports sind auf dem Router offen?`
- `Prüfe Ports 1-1000 auf 192.168.1.10`
- `Schneller Portscan auf 192.168.1.0/24` *(mit T4 Timing)*

> **Gut zu wissen:**
> - Ohne Port-Angabe werden die 100 häufigsten Ports geprüft
> - Du kannst einzelne Ports (`22,80,443`) oder Bereiche (`1-1000`) angeben
> - "Schnell" oder "langsam" steuert die Scan-Geschwindigkeit
> - Manche Geräte antworten nicht auf Ping - sag dann "auch wenn kein Ping"

**Service-Erkennung:**
- `Welche Services laufen auf 192.168.1.1?`
- `Erkenne die Versionen auf dem Router`
- `Was für ein Webserver läuft auf 192.168.1.10:80?`
- `Gründliche Service-Erkennung auf 192.168.1.5` *(mit hoher Intensität)*

> **Gut zu wissen:**
> - Erkennt Service-Namen und Versionen (z.B. "OpenSSH 8.9", "Apache 2.4")
> - Langsamer als Port-Scan, dafür mehr Details
> - "Gründlich" oder "intensiv" für bessere Erkennung, "schnell" für oberflächlich
> - Ohne Port-Angabe werden die 20 häufigsten Ports geprüft

**Web-Suche (nur mit Docker Compose):**
- `Suche nach nmap scripting Dokumentation`
- `Was ist SearXNG?`
- `Finde Tutorials zu Python Netzwerk-Programmierung`

> **Gut zu wissen:**
> - Web-Suche funktioniert nur mit Docker Compose (`docker compose up`)
> - Alle Suchanfragen bleiben lokal (kein externer API-Key nötig)
> - Kategorien verfügbar: general, images, news, science, it, files

**Folgefragen stellen:**
- `Welche davon haben offene Ports?`
- `Was läuft auf 192.168.1.10?`
- `Gibt es Webserver im Netzwerk?`

**Tipps:**
- Für Netzwerk-Scans brauchst du eine Netzwerk-Angabe (z.B. `192.168.1.0/24`)
- DNS-Abfragen funktionieren mit jedem Hostnamen oder IP
- Der Agent merkt sich vorherige Ergebnisse - du kannst Folgefragen stellen
- Formuliere so, wie du einen Kollegen fragen würdest

### Befehle
- `/help` - Verfügbare Befehle anzeigen
- `/tools` - Verfügbare Tools auflisten (Name + Beschreibung)
- `/config` - LLM-Konfiguration anzeigen (Model, Base URL, Context-Limit)
- `/status` - Session-Statistik anzeigen (Tokens, Context-Auslastung, Truncations)
- `/version` - Version anzeigen
- `/clear` - Session-Speicher löschen
- `/exit` - Beenden

## Plattform-Kompatibilität

| System | LAN-Scan | Methode | Wie starten? |
|--------|----------|---------|--------------|
| Linux | Vollständig | ICMP Ping | `--network host` |
| Windows + WSL2 | Vollständig | ICMP Ping | Im WSL-Terminal |
| Windows (PowerShell) | Ja | TCP-Connect | Normal starten |
| macOS | Ja | TCP-Connect | Normal starten |

**Automatische Erkennung:** Der Agent erkennt automatisch, ob ICMP-Ping möglich ist. Falls nicht (Docker auf Windows/macOS), wird automatisch TCP-Connect Scan verwendet.

## Sicherheit

Der Network Agent ist für **lokale Netzwerk-Analyse** konzipiert:

| Was ist erlaubt? | Was ist blockiert? |
|------------------|-------------------|
| Private IPs (192.168.x.x, 10.x.x.x, 172.16-31.x.x) | Öffentliche IPs (Internet) |
| Loopback (127.0.0.1) | IPv6-Adressen |
| Dein lokales Netzwerk | Link-Local (169.254.x.x) |

**Warum diese Einschränkungen?**
- Verhindert versehentliches Scannen fremder Systeme im Internet
- Schützt vor Missbrauch als Angriffswerkzeug
- Fokussiert auf den eigentlichen Anwendungsfall: Heimnetzwerk-Analyse

**Du willst trotzdem ein bestimmtes Netzwerk scannen?**
Konfiguriere Ausnahmen in `config/settings.yaml` (siehe Scan-Einstellungen oben).

<details>
<summary><strong>Technische Details zu den Tools</strong></summary>

### Host-Limits

| Tool | Max Hosts | Netzwerk | Grund |
|------|-----------|----------|-------|
| ping_sweep | 65.536 | /16 | Schnell: 1 Probe pro Host |
| port_scanner | 256 | /24 | Langsam: viele Probes pro Port |
| service_detect | 256 | /24 | Sehr langsam: mehrere Probes pro Service |
| dns_lookup | 1 | Einzeln | DNS-Abfragen sind immer einzeln |

**Warum der Unterschied?** Discovery (ping_sweep) sendet nur einen Probe pro Host und ist deshalb schnell. Port- und Service-Scans senden viele Probes pro Host und würden bei großen Netzwerken sehr lange dauern.

### Port-Defaults

| Tool | Default Ports | Konfigurierbar? |
|------|---------------|-----------------|
| ping_sweep | 22, 80, 443, 8080 | Nein (fest) |
| port_scanner | Top 100 | Ja (`ports` Parameter) |
| service_detect | Top 20 | Ja (`ports` Parameter) |

### IPv6 Support

**Status:** Nicht unterstützt (nicht geplant)

Alle Tools lehnen IPv6-Adressen ab (z.B. `::1`, `fe80::1`, `2001:db8::1`). Der Fokus liegt auf IPv4 Heimnetzwerken.

### DNS Lookup Exception

Das `dns_lookup` Tool ist das einzige Tool, das öffentliche Domains abfragen darf. Das ist bewusst so, weil DNS-Abfragen keine Scans sind - sie fragen nur DNS-Server ab.

</details>

## Aktualisieren

Um auf die neueste Version zu aktualisieren:

```bash
# 1. Neuesten Code holen
cd network-agent
git pull

# 2. Docker Image neu bauen (WICHTIG!)
docker build -t network-agent:latest .

# 3. Agent starten
docker run -it --rm --network host --env-file .env network-agent:latest
```

**Wann neu bauen?**
- Nach jedem `git pull` (Code-Änderungen)
- Nach Änderungen an `requirements.txt`
- Nach Änderungen am `Dockerfile`

**Tipp:** Die Convenience Scripts (`start.sh`, `start.bat`) bauen das Image nur, wenn es noch nicht existiert. Nach Updates musst du `docker build` manuell ausführen oder das alte Image löschen:
```bash
docker rmi network-agent:latest
./start.sh
```

## Troubleshooting

> **Für Entwickler:** Projektstruktur und wie du eigene Tools hinzufügst findest du [am Ende dieser Seite](#für-entwickler-projektstruktur--eigene-tools).

<details>
<summary><strong>"LLM_API_KEY environment variable not set"</strong></summary>

Die `.env` Datei fehlt oder enthält keinen Key.

**Lösung:**
```bash
cp .env.example .env
# Dann .env bearbeiten und deinen API Key eintragen
```
</details>

<details>
<summary><strong>"Error: Scan timeout"</strong></summary>

Der Scan dauert zu lange und bricht ab.

**Mögliche Ursachen:**
- Netzwerk zu groß (z.B. /16 statt /24)
- Netzwerk nicht erreichbar
- Firewall blockiert Pakete

**Lösungen:**
1. Kleineres Subnetz versuchen: `/28` (16 Hosts) statt `/24` (256 Hosts)
2. Timeout in `config/settings.yaml` erhöhen: `timeout: 300`
3. Prüfen ob du im richtigen Netzwerk bist
</details>

<details>
<summary><strong>Keine Geräte gefunden</strong></summary>

Der Scan läuft durch, findet aber nichts.

**Auf Windows/macOS:**
TCP-Connect Scan findet nur Geräte mit offenen Standard-Ports (22, 80, 443...).
→ Für vollständige Erkennung: WSL2 auf Windows nutzen

**Auf Linux:**
- Bist du im richtigen Netzwerk? Prüfe mit `ip addr`
- Ist `--network host` beim Docker-Start gesetzt?
- Firewall auf dem Host-System prüfen
</details>

<details>
<summary><strong>"Validation error: Public IP not allowed"</strong></summary>

Du versuchst eine öffentliche IP oder ein Internet-Netzwerk zu scannen.

**Warum?** Der Agent ist nur für lokale Netzwerke gedacht.

**Lösung:** Nutze private IP-Bereiche:
- `192.168.x.x/24` (Heimnetzwerke)
- `10.x.x.x/24` (Firmennetzwerke)
- `172.16-31.x.x/24` (Docker, VPNs)
</details>

<details>
<summary><strong>Model nicht gefunden / API Error</strong></summary>

Der LLM-Provider antwortet mit einem Fehler.

**Prüfe in `config/settings.yaml`:**
- Ist `model` korrekt geschrieben? (z.B. `gpt-4` nicht `GPT-4`)
- Ist `base_url` für deinen Provider richtig?
- Unterstützt dein Provider Tool/Function Calling?

**Prüfe deinen API Key:**
- Ist der Key in `.env` korrekt?
- Hat der Key genug Guthaben/Credits?
- Ist der Key für das gewählte Model berechtigt?
</details>

<details>
<summary><strong>Agent antwortet nicht sinnvoll</strong></summary>

Die KI versteht deine Frage nicht oder gibt seltsame Antworten.

**Tipps:**
- Sei spezifischer: `Scanne 192.168.1.0/24` statt `Scanne mein Netzwerk`
- Gib das Netzwerk immer mit an
- Nutze `/clear` um die Session zurückzusetzen
- Probiere ein anderes/größeres Model (z.B. gpt-4 statt gpt-3.5)
</details>

---

<details>
<summary><strong>Für Entwickler: Projektstruktur & eigene Tools</strong></summary>

### Dateien im Projekt

```
network-agent/
├── cli.py              # Hauptprogramm (REPL)
├── agent/
│   ├── core.py         # KI-Agent mit Tool-Loop + Session Memory
│   └── llm.py          # LLM Client (OpenAI-kompatibel)
├── tools/
│   ├── base.py         # Tool-Basisklasse
│   ├── config.py       # Scan-Konfiguration (Singleton)
│   ├── validation.py   # Input-Validierung
│   ├── network/        # Netzwerk-Tools
│   │   ├── ping_sweep.py
│   │   ├── dns_lookup.py
│   │   ├── port_scanner.py
│   │   └── service_detect.py
│   └── web/            # Web-Tools
│       └── web_search.py   # SearXNG Web-Suche
├── config/
│   ├── settings.yaml   # Provider & Scan Konfiguration
│   └── prompts/
│       └── system.md   # System-Prompt für KI
├── searxng/            # SearXNG Konfiguration
│   └── settings.yml    # Suchmaschinen-Konfiguration
├── docker-compose.yml  # Linux (mit Host-Network)
├── docker-compose.macos.yml  # macOS/Windows (mit Bridge-Network)
├── Dockerfile          # Container-Definition
├── requirements.txt    # Python-Abhängigkeiten
└── .env.example        # API-Key Vorlage
```

### Eigene Tools hinzufügen

1. Neue Datei unter `tools/` erstellen
2. Von `BaseTool` erben und `name`, `description`, `parameters`, `execute` implementieren
3. In `tools/__init__.py` registrieren

Beispiel siehe `tools/network/ping_sweep.py`.

</details>

## Lizenz

MIT
