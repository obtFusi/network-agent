# Network Agent

[![Version](https://img.shields.io/badge/version-0.3.0-blue.svg)](CHANGELOG.md)

Ein KI-gesteuerter Netzwerk-Scanner. Statt komplizierte Terminal-Befehle zu lernen, stellst du einfach Fragen wie *"Welche Geräte sind in meinem Netzwerk?"* - der Agent erledigt den Rest.

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

### 3. Docker Image erstellen

```bash
docker build -t network-agent:latest .
```

### 4. Agent starten

**Linux:**
```bash
docker run -it --rm --network host --env-file .env network-agent:latest
```

**Windows mit WSL2:**
```bash
docker run -it --rm --network host --env-file .env network-agent:latest
```

**Windows ohne WSL / macOS:**
```bash
docker run -it --rm --env-file .env network-agent:latest
```
*Hinweis: Ohne `--network host` ist der Scan auf das Docker-interne Netzwerk beschränkt.*

## Verwendung

Nach dem Start siehst du:
```
Network Agent startet...
   Model: gpt-4
   Type 'exit' to stop, 'clear' to reset session

   Context-Limit: 8,192 tokens

>
```

Jetzt kannst du Fragen stellen:
- `Welche Geräte sind im Netzwerk 192.168.1.0/24?`
- `Scanne das Netzwerk 10.0.0.0/24`
- `Wer ist online im Subnetz 192.168.178.0/24?`

**Commands:**
- `clear` / `reset` - Session-Speicher löschen
- `exit` / `quit` - Beenden

## Plattform-Kompatibilität

| System | LAN-Scan | Methode | Wie starten? |
|--------|----------|---------|--------------|
| Linux | Vollständig | ICMP Ping | `--network host` |
| Windows + WSL2 | Vollständig | ICMP Ping | Im WSL-Terminal |
| Windows (PowerShell) | Ja | TCP-Connect | Normal starten |
| macOS | Ja | TCP-Connect | Normal starten |

**Automatische Erkennung:** Der Agent erkennt automatisch, ob ICMP-Ping möglich ist. Falls nicht (Docker auf Windows/macOS), wird automatisch TCP-Connect Scan verwendet.

## Troubleshooting

**"LLM_API_KEY environment variable not set"**
Die `.env` Datei fehlt oder enthält keinen Key.

**"Error: Scan timeout"**
Netzwerk zu groß oder nicht erreichbar. Kleineres Subnetz versuchen (z.B. /28 statt /24).

**Keine Geräte gefunden (Windows/macOS)**
TCP-Connect Scan findet nur Geräte mit offenen Standard-Ports. Für vollständige Erkennung: WSL2 nutzen.

**Model nicht gefunden / API Error**
Prüfe in `config/settings.yaml`:
- Ist `model` korrekt geschrieben?
- Ist `base_url` für deinen Provider richtig?
- Unterstützt dein Provider Tool Calling?

## Dateien im Projekt

```
network-agent/
├── cli.py              # Hauptprogramm (REPL)
├── agent/
│   ├── core.py         # KI-Agent mit Tool-Loop + Session Memory
│   └── llm.py          # LLM Client (OpenAI-kompatibel)
├── tools/
│   ├── base.py         # Tool-Basisklasse
│   └── network/
│       └── ping_sweep.py   # nmap Ping-Sweep
├── config/
│   ├── settings.yaml   # Provider & Model Konfiguration
│   └── prompts/
│       └── system.md   # System-Prompt für KI
├── Dockerfile          # Container-Definition
├── requirements.txt    # Python-Abhängigkeiten
└── .env.example        # API-Key Vorlage
```

## Eigene Tools hinzufügen

1. Neue Datei unter `tools/` erstellen
2. Von `BaseTool` erben und `name`, `description`, `parameters`, `execute` implementieren
3. In `tools/__init__.py` registrieren

Beispiel siehe `tools/network/ping_sweep.py`.

## Lizenz

MIT
