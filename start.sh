#!/bin/bash
# Network Agent Startscript (Linux/macOS/WSL2)

if [ ! -f .env ]; then
    echo "Fehler: .env Datei nicht gefunden!"
    echo "Bitte erstelle eine .env Datei mit deinem Venice.ai API Key:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
fi

# Image bauen falls nicht vorhanden
if ! docker image inspect network-agent:latest >/dev/null 2>&1; then
    echo "Baue Docker Image..."
    docker build -t network-agent:latest .
fi

# Agent starten
docker run -it --rm --network host --env-file .env network-agent:latest
