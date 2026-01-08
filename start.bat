@echo off
REM Network Agent Startscript (Windows)

if not exist .env (
    echo Fehler: .env Datei nicht gefunden!
    echo Bitte erstelle eine .env Datei mit deinem Venice.ai API Key:
    echo   copy .env.example .env
    echo   notepad .env
    pause
    exit /b 1
)

REM Image bauen falls nicht vorhanden
docker image inspect network-agent:latest >nul 2>&1
if errorlevel 1 (
    echo Baue Docker Image...
    docker build -t network-agent:latest .
)

REM Agent starten (ohne --network host, funktioniert nicht unter Windows)
echo HINWEIS: Fuer vollen LAN-Zugriff starte dieses Script in WSL2
docker run -it --rm --env-file .env network-agent:latest
