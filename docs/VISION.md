# Network Agent - Enterprise Vision

## Ziel

Enterprise-grade Network Pentesting & Policy Compliance Platform.

## Endausbau Features

```
Network Agent Enterprise
├── Multi-User (Pentester-Teams, Audit Trail)
├── Distributed Scanning (mehrere Scan-Agents)
├── Policy Engine (Compliance-Checks, Regelwerke)
├── Scheduling (automatische Scans)
├── Reporting (PDF, SIEM-Integration)
├── Web UI (Dashboards, Findings)
├── API (REST/GraphQL für Integration)
└── RAG Knowledge Base (CVEs, Best Practices, Policies)
```

---

## Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│                     docker-compose / K8s                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Web UI    │  │  REST API   │  │      CLI Agent          │ │
│  │  (React)    │  │  (FastAPI)  │  │   (für Pentester)       │ │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘ │
│         │                │                      │               │
│         └────────────────┼──────────────────────┘               │
│                          │                                      │
│                    ┌─────▼─────┐                                │
│                    │  Message  │                                │
│                    │   Queue   │  (Redis/RabbitMQ)              │
│                    └─────┬─────┘                                │
│                          │                                      │
│    ┌─────────────────────┼─────────────────────┐                │
│    │                     │                     │                │
│    ▼                     ▼                     ▼                │
│ ┌──────────┐      ┌──────────┐          ┌──────────┐           │
│ │  Scan    │      │  Scan    │   ...    │  Scan    │           │
│ │ Worker 1 │      │ Worker 2 │          │ Worker N │           │
│ └────┬─────┘      └────┬─────┘          └────┬─────┘           │
│      │                 │                     │                  │
│      └─────────────────┼─────────────────────┘                  │
│                        │                                        │
│                        ▼                                        │
│              ┌─────────────────┐                                │
│              │    PostgreSQL   │                                │
│              │  (Main DB)      │                                │
│              └────────┬────────┘                                │
│                       │                                         │
│         ┌─────────────┼─────────────┐                           │
│         ▼             ▼             ▼                           │
│    ┌─────────┐  ┌──────────┐  ┌──────────┐                     │
│    │ Milvus/ │  │  LLM     │  │ Policy   │                     │
│    │Qdrant   │  │ Service  │  │ Engine   │                     │
│    │(Vector) │  │(Venice)  │  │          │                     │
│    └─────────┘  └──────────┘  └──────────┘                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Services

| Service | Technologie | Zweck |
|---------|-------------|-------|
| **API Gateway** | FastAPI | REST/GraphQL, Auth |
| **Web UI** | React/Next.js | Dashboard, Reports |
| **CLI Agent** | Python | Pentester-Interface |
| **Scan Workers** | Python + nmap/nuclei | Verteilte Scans |
| **Message Queue** | Redis/RabbitMQ | Job-Verteilung |
| **Main DB** | PostgreSQL | Scans, Users, Findings |
| **Vector DB** | Milvus/Qdrant | RAG, Semantic Search |
| **LLM Service** | Venice.ai/OpenAI | AI-Analyse |
| **Policy Engine** | Python/OPA | Compliance-Checks |

---

## Database Schema

```sql
-- Users & Auth
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE,
    role TEXT,  -- admin, pentester, viewer
    created_at TIMESTAMPTZ
);

-- Projects (Kunden/Engagements)
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    name TEXT,
    client TEXT,
    scope JSONB,  -- Erlaubte Netzwerke
    start_date DATE,
    end_date DATE
);

-- Scan Jobs
CREATE TABLE scan_jobs (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    user_id UUID REFERENCES users(id),
    type TEXT,  -- ping_sweep, port_scan, vuln_scan
    target TEXT,
    status TEXT,  -- pending, running, completed, failed
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    worker_id TEXT
);

-- Findings
CREATE TABLE findings (
    id UUID PRIMARY KEY,
    scan_job_id UUID REFERENCES scan_jobs(id),
    host TEXT,
    port INTEGER,
    severity TEXT,  -- critical, high, medium, low, info
    title TEXT,
    description TEXT,
    evidence TEXT,
    cve_ids TEXT[],
    remediation TEXT,
    status TEXT  -- open, confirmed, false_positive, remediated
);

-- Policy Rules
CREATE TABLE policies (
    id UUID PRIMARY KEY,
    name TEXT,
    description TEXT,
    rule JSONB,  -- Policy Definition
    severity TEXT,
    enabled BOOLEAN
);

-- Policy Violations
CREATE TABLE violations (
    id UUID PRIMARY KEY,
    scan_job_id UUID REFERENCES scan_jobs(id),
    policy_id UUID REFERENCES policies(id),
    host TEXT,
    details JSONB
);

-- Audit Log (Compliance)
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    user_id UUID,
    action TEXT,
    resource_type TEXT,
    resource_id UUID,
    details JSONB
);

-- Sessions & Memory
CREATE TABLE sessions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    summary TEXT
);

CREATE TABLE messages (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID REFERENCES sessions(id),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    role TEXT,  -- user, assistant, tool, system
    content TEXT,
    tool_name TEXT,
    tool_args JSONB,
    tokens INTEGER
);

-- Vector Embeddings (für RAG)
CREATE TABLE embeddings (
    id BIGSERIAL PRIMARY KEY,
    source_type TEXT,  -- message, finding, policy, cve
    source_id UUID,
    chunk_text TEXT,
    vector vector(384)  -- pgvector extension
);

-- Indexes
CREATE INDEX idx_messages_session ON messages(session_id);
CREATE INDEX idx_scan_jobs_project ON scan_jobs(project_id);
CREATE INDEX idx_scan_jobs_status ON scan_jobs(status);
CREATE INDEX idx_findings_severity ON findings(severity);
CREATE INDEX idx_findings_host ON findings(host);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX idx_embeddings_vector ON embeddings USING ivfflat (vector vector_cosine_ops);
```

---

## Docker Compose (Enterprise)

```yaml
version: '3.8'

services:
  # API Gateway
  api:
    build: ./services/api
    ports:
      - "8080:8080"
    depends_on:
      - db
      - redis
      - vectordb
    environment:
      - DATABASE_URL=postgresql://agent:${DB_PASSWORD}@db:5432/networkagent
      - REDIS_URL=redis://redis:6379
      - LLM_API_KEY=${VENICE_API_KEY}

  # Web UI
  web:
    build: ./services/web
    ports:
      - "3000:3000"
    depends_on:
      - api

  # Scan Workers (skalierbar)
  scan-worker:
    build: ./services/scanner
    deploy:
      replicas: 3
    depends_on:
      - redis
      - db
    cap_add:
      - NET_RAW
      - NET_ADMIN
    network_mode: host

  # PostgreSQL
  db:
    image: postgres:16
    volumes:
      - postgres-data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=networkagent
      - POSTGRES_USER=agent
      - POSTGRES_PASSWORD=${DB_PASSWORD}

  # Redis (Queue + Cache)
  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data

  # Vector DB für RAG
  vectordb:
    image: qdrant/qdrant
    volumes:
      - qdrant-data:/qdrant/storage
    ports:
      - "6333:6333"

  # Policy Engine (OPA)
  policy-engine:
    image: openpolicyagent/opa
    volumes:
      - ./policies:/policies
    command: run --server /policies
    ports:
      - "8181:8181"

volumes:
  postgres-data:
  redis-data:
  qdrant-data:
```

---

## Entwicklungs-Roadmap

### Phase 1: Foundation (aktuell)
- [x] CLI Agent Grundstruktur
- [x] Basic Tools (ping_sweep)
- [x] Input Validation / Guardrails
- [x] Cross-Platform Support
- [ ] Session Memory
- [ ] SQLite mit migrationsfreundlichem Schema

### Phase 2: Core Services
- [ ] PostgreSQL Migration
- [ ] FastAPI Backend
- [ ] Scan Worker Architecture
- [ ] Job Queue (Redis)
- [ ] Basic Auth (JWT)

### Phase 3: Enterprise Features
- [ ] User Management & RBAC
- [ ] Project/Scope Management
- [ ] Policy Engine (OPA Integration)
- [ ] Audit Logging
- [ ] Scheduling

### Phase 4: Intelligence
- [ ] Vector DB + RAG
- [ ] CVE Database Integration
- [ ] AI-powered Analysis
- [ ] Remediation Suggestions
- [ ] Threat Intelligence Feeds

### Phase 5: UI & Reporting
- [ ] Web Dashboard
- [ ] Real-time Scan Monitoring
- [ ] PDF/HTML Reports
- [ ] SIEM Integration (Splunk, ELK)
- [ ] Alerting (Email, Slack, Webhook)

---

## Scan Tools Roadmap

### Phase 1 (PoC)
- [x] `ping_sweep` - Host Discovery

### Phase 2 (Core)
- [ ] `port_scan` - TCP/UDP Port Scanning
- [ ] `service_detection` - Service/Version Detection
- [ ] `os_detection` - OS Fingerprinting

### Phase 3 (Vulnerability)
- [ ] `vuln_scan` - Nuclei Integration
- [ ] `ssl_check` - SSL/TLS Analysis
- [ ] `http_probe` - Web Server Analysis

### Phase 4 (Compliance)
- [ ] `policy_check` - Policy Compliance
- [ ] `cis_benchmark` - CIS Benchmark Checks
- [ ] `password_audit` - Weak Credential Detection

### Phase 5 (Advanced)
- [ ] `dns_enum` - DNS Enumeration
- [ ] `subdomain_scan` - Subdomain Discovery
- [ ] `cloud_scan` - AWS/Azure/GCP Misconfiguration

---

## Design Principles

1. **Security First** - Input Validation, Least Privilege, Audit Trail
2. **Scalability** - Horizontal scaling via Workers
3. **Modularity** - Plugins für neue Tools/Policies
4. **AI-Native** - LLM-Integration in jedem Layer
5. **Compliance-Ready** - Audit Logs, Reports, RBAC

---

## Technologie-Stack

| Layer | Technologie |
|-------|-------------|
| Frontend | React, Next.js, TailwindCSS |
| API | FastAPI, Pydantic, SQLAlchemy |
| Queue | Redis, Celery |
| Database | PostgreSQL, pgvector |
| Vector DB | Qdrant |
| Scanning | nmap, nuclei, custom tools |
| Policy | Open Policy Agent (OPA) |
| LLM | Venice.ai, OpenAI-compatible |
| Container | Docker, docker-compose |
| Orchestration | Kubernetes (optional) |
| CI/CD | GitHub Actions |
