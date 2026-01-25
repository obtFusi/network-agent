# CI/CD Dashboard Frontend

React-basiertes Web-Dashboard für Pipeline-Monitoring, Approval-Queue und Live-Logs.

## Stack

- **React 18** mit TypeScript
- **Vite** als Build-Tool
- **TailwindCSS** für Styling
- **React Router** für Navigation
- **Server-Sent Events (SSE)** für Real-time Updates

## Entwicklung

```bash
# Dependencies installieren
npm install

# Dev-Server starten (Port 5173)
npm run dev

# Type-Check
npm run type-check

# Lint
npm run lint

# Production Build
npm run build
```

## Struktur

```
src/
├── api/
│   └── client.ts       # API Client + SSE
├── components/
│   ├── Layout.tsx      # App Layout mit Navigation
│   ├── PipelineList.tsx    # Pipeline-Übersicht
│   ├── PipelineCard.tsx    # Pipeline-Karte
│   ├── PipelineDetail.tsx  # Pipeline-Detail mit Steps
│   ├── ApprovalQueue.tsx   # Pending Approvals
│   ├── ApprovalCard.tsx    # Approval-Aktionen
│   ├── StatusBadge.tsx     # Status-Anzeige
│   └── LogViewer.tsx       # Log-Anzeige
├── hooks/
│   ├── usePipelines.ts     # Pipeline-Daten
│   ├── useApprovals.ts     # Approval-Daten
│   └── useEventStream.ts   # SSE-Verbindung
├── types/
│   └── index.ts        # TypeScript Types
├── styles/
│   └── globals.css     # TailwindCSS + Custom Styles
├── App.tsx             # Router Setup
└── main.tsx            # Entry Point
```

## Features

- **Pipeline-Liste**: Übersicht aller Pipelines mit Status
- **Pipeline-Detail**: Steps, Logs, Retry/Abort-Aktionen
- **Approval-Queue**: Pending Approvals mit Approve/Reject
- **Real-time Updates**: SSE-basierte Live-Updates
- **Connection Status**: Anzeige der SSE-Verbindung

## API-Proxy

Der Vite Dev-Server ist so konfiguriert, dass `/api/*` Requests an `http://localhost:8000` weitergeleitet werden. Dies ermöglicht die Entwicklung ohne CORS-Probleme.

## Production Deployment

```bash
npm run build
# Output in dist/
```

Das `dist/`-Verzeichnis kann von einem statischen Webserver oder dem FastAPI-Backend ausgeliefert werden.
