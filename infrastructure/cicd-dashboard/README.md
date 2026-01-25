# CI/CD Dashboard

FastAPI-basiertes CI/CD System mit React-Frontend für Pipeline-Orchestrierung, Approval-Workflows und Real-time Monitoring.

## Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                        │
│  PipelineList │ PipelineDetail │ ApprovalQueue │ LogViewer │
└───────────────────────────┬─────────────────────────────────┘
                            │ SSE / REST
┌───────────────────────────┴─────────────────────────────────┐
│                     Backend (FastAPI)                        │
│  /pipelines │ /webhooks │ /approvals │ /events              │
├─────────────────────────────────────────────────────────────┤
│  Services: PipelineExecutor │ ApprovalService │ EventBus    │
├─────────────────────────────────────────────────────────────┤
│                   SQLite (async, aiosqlite)                 │
└─────────────────────────────────────────────────────────────┘
```

## Features

- **Pipeline Orchestrierung**: Multi-Step Pipelines mit Stage-basierter Ausführung
- **Webhook Integration**: GitHub/GitLab Webhook-Empfänger
- **Approval Workflows**: Manuelle Genehmigung für kritische Schritte
- **Real-time Updates**: Server-Sent Events (SSE) für Live-Status
- **Log Streaming**: Echtzeit-Logs während der Ausführung
- **React Dashboard**: Modernes Web-UI für Monitoring

## Quick Start

### Backend

```bash
# Virtual Environment erstellen
python -m venv .venv
source .venv/bin/activate

# Dependencies installieren
pip install -r requirements.txt

# Server starten
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend

# Dependencies installieren
npm install

# Dev-Server starten
npm run dev
```

### Beide zusammen

```bash
# Terminal 1: Backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
# → http://localhost:5173 (proxied API requests to :8000)
```

## API Endpoints

| Endpoint | Beschreibung |
|----------|--------------|
| `POST /api/v1/webhooks/{source}` | Webhook-Empfänger (github, gitlab) |
| `GET /api/v1/pipelines` | Pipeline-Liste |
| `GET /api/v1/pipelines/{id}` | Pipeline-Details mit Steps |
| `POST /api/v1/pipelines/{id}/start` | Pipeline starten |
| `POST /api/v1/pipelines/{id}/abort` | Pipeline abbrechen |
| `GET /api/v1/approvals/pending` | Pending Approvals |
| `POST /api/v1/approvals/{id}/approve` | Approval genehmigen |
| `POST /api/v1/approvals/{id}/reject` | Approval ablehnen |
| `GET /api/v1/events/stream` | SSE Event-Stream |

## Dokumentation

- [API Design](docs/api-design.md)
- [Pipeline Orchestration](docs/pipeline-orchestration.md)
- [SSE Events](docs/sse-events.md)
- [Frontend README](frontend/README.md)

## Tests

```bash
# Backend Tests
pytest tests/ -v

# Frontend Type-Check
cd frontend && npm run type-check

# Frontend Lint
cd frontend && npm run lint
```

## Projektstruktur

```
cicd-dashboard/
├── app/
│   ├── api/           # FastAPI Router
│   ├── db/            # Database Layer
│   ├── models/        # SQLAlchemy Models
│   ├── schemas/       # Pydantic Schemas
│   ├── services/      # Business Logic
│   └── main.py        # App Entry Point
├── docs/              # Dokumentation
├── frontend/          # React Frontend
│   ├── src/
│   │   ├── api/       # API Client
│   │   ├── components/
│   │   ├── hooks/
│   │   └── types/
│   └── package.json
├── tests/             # Backend Tests
└── requirements.txt
```
