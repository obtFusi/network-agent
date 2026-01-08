# Network Agent

Ein KI-gesteuerter Netzwerk-Scanner. Statt komplizierte Terminal-Befehle zu lernen, stellst du einfach Fragen wie *"Welche Geräte sind in meinem Netzwerk?"* - der Agent erledigt den Rest.

## Was macht dieses Tool?

Der Network Agent kombiniert:
- **Natürliche Sprache**: Du fragst auf Deutsch, was du wissen willst
- **KI-Verarbeitung**: Venice.ai (llama-3.3-70b) versteht deine Anfrage
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

## Voraussetzungen

1. **Docker** - [Download Docker Desktop](https://www.docker.com/products/docker-desktop/)
2. **Venice.ai API Key** - Kostenlos unter [venice.ai](https://venice.ai) registrieren

## Installation (Schritt für Schritt)

### Schritt 1: Repository herunterladen

Öffne ein Terminal (Windows: PowerShell, macOS/Linux: Terminal) und führe aus:

```bash
git clone https://github.com/obtFusi/network-agent.git
cd network-agent
```

### Schritt 2: API Key einrichten

Kopiere die Beispiel-Konfiguration:

**Windows (PowerShell):**
```powershell
copy .env.example .env
```

**macOS/Linux:**
```bash
cp .env.example .env
```

Öffne die `.env` Datei mit einem Texteditor und trage deinen Venice.ai API Key ein:
```
VENICE_API_KEY=dein_api_key_hier
```

### Schritt 3: Docker Image erstellen

```bash
docker build -t network-agent:latest .
```

Das dauert beim ersten Mal 1-2 Minuten (Downloads).

### Schritt 4: Agent starten

**Linux:**
```bash
docker run -it --rm --network host --env-file .env network-agent:latest
```

**Windows mit WSL2 (empfohlen für volle Funktionalität):**

Öffne ein WSL-Terminal und führe aus:
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
   Model: llama-3.3-70b
   Type 'exit' or 'quit' to stop

>
```

Jetzt kannst du Fragen stellen:
- `Welche Geräte sind im Netzwerk 192.168.1.0/24?`
- `Scanne das Netzwerk 10.0.0.0/24`
- `Wer ist online im Subnetz 192.168.178.0/24?`

Beenden mit `exit` oder `quit`.

## Plattform-Kompatibilität

| System | LAN-Scan möglich? | Wie starten? |
|--------|-------------------|--------------|
| Linux | Ja | `--network host` verwenden |
| Windows + WSL2 | Ja | Im WSL-Terminal starten |
| Windows (nur PowerShell) | Eingeschränkt | Nur Docker-Netzwerk sichtbar |
| macOS | Eingeschränkt | Nur Docker-Netzwerk sichtbar |

**Warum die Einschränkung?** Docker unter Windows/macOS läuft in einer VM. `--network host` (direkter Netzwerkzugriff) funktioniert nur unter Linux bzw. WSL2.

## Troubleshooting

**"VENICE_API_KEY environment variable not set"**
→ Die `.env` Datei fehlt oder enthält keinen gültigen Key.

**"Error: Scan timeout"**
→ Das Netzwerk ist zu groß oder nicht erreichbar. Versuche ein kleineres Subnetz (z.B. /28 statt /24).

**Keine Geräte gefunden (Windows/macOS)**
→ Ohne WSL2 kannst du nur Docker-interne Netzwerke scannen. Installiere [WSL2](https://docs.microsoft.com/de-de/windows/wsl/install).

## Wie funktioniert es technisch?

```
Du: "Welche Geräte sind online?"
         ↓
    Venice.ai LLM
    (versteht Anfrage, wählt Tool)
         ↓
    ping_sweep Tool
    (führt "nmap -sn" aus)
         ↓
    Venice.ai LLM
    (interpretiert nmap-Output)
         ↓
Du: "5 Geräte gefunden: ..."
```

## Dateien im Projekt

```
network-agent/
├── cli.py              # Hauptprogramm (REPL)
├── agent/
│   ├── core.py         # KI-Agent mit Tool-Loop
│   └── llm.py          # Venice.ai Verbindung
├── tools/
│   ├── base.py         # Tool-Basisklasse
│   └── network/
│       └── ping_sweep.py   # nmap Ping-Sweep
├── config/
│   ├── settings.yaml   # Konfiguration
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
