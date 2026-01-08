# Network Agent

CLI-Agent für Netzwerk-Analyse via natürlicher Sprache. Nutzt Venice.ai (llama-3.3-70b) mit Function Calling.

## Quick Start

```bash
# 1. .env erstellen
cp .env.example .env
# API Keys eintragen (VENICE_API_KEY)

# 2. Docker Image bauen
docker build -t network-agent:latest .

# 3. Starten
docker run -it --rm \
  --network host \
  --env-file .env \
  network-agent:latest
```

## Verwendung

```
> Welche Geräte sind im Netzwerk 192.168.1.0/24?
[Agent scannt mit nmap und interpretiert Ergebnisse]
```

## Verfügbare Tools

- **ping_sweep**: Scannt Netzwerk nach aktiven Hosts (nmap -sn)

## Architektur

```
cli.py          → Entry Point (REPL)
agent/core.py   → Tool-Calling Loop
agent/llm.py    → Venice.ai Wrapper
tools/          → Tool Framework
  base.py       → BaseTool Abstraktion
  network/      → Network Tools
    ping_sweep.py
config/         → Settings + Prompts
```

## Erweiterung

Neues Tool hinzufügen:
1. Tool-Klasse erstellen (erbt von `BaseTool`)
2. In `tools/__init__.py` registrieren

## Requirements

- Docker
- Venice.ai API Key (https://venice.ai)
