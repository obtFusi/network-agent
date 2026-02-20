"""Tests for Findings API endpoints."""

import pytest
from fastapi.testclient import TestClient

from agent.api.app import create_app
from tools.findings_store import FindingsStore


@pytest.fixture
def test_config():
    """Minimal config for testing."""
    return {
        "version": "test",
        "llm": {
            "provider": {
                "model": "test-model",
                "base_url": "http://localhost:11434/v1",
            }
        },
    }


@pytest.fixture
def test_system_prompt():
    """Minimal system prompt for testing."""
    return "You are a test agent."


@pytest.fixture
def findings_store(tmp_path):
    """Create a FindingsStore with test data."""
    db_path = str(tmp_path / "test_findings.db")
    store = FindingsStore(db_path=db_path, retention_days=0)

    # Add test data
    run_id = store.start_scan_run(
        session_id="test-session-1",
        tool_name="port_scanner",
        target="192.0.2.1",
        args={"ports": "80,443"},
    )
    store.complete_scan_run(run_id, status="completed")

    store.add_finding(
        session_id="test-session-1",
        scan_run_id=run_id,
        host="192.0.2.1",
        port=80,
        protocol="tcp",
        severity="high",
        tool_name="port_scanner",
        title="Open HTTP port",
        description="Port 80 is open and serving HTTP",
        evidence="Nmap scan result",
        remediation="Close port or restrict access",
    )
    store.add_finding(
        session_id="test-session-1",
        scan_run_id=run_id,
        host="192.0.2.1",
        port=443,
        protocol="tcp",
        severity="info",
        tool_name="port_scanner",
        title="Open HTTPS port",
        description="Port 443 is open",
    )

    # Add a denied scan run
    denied_id = store.start_scan_run(
        session_id="test-session-1",
        tool_name="llmnr_poisoner",
        target="192.0.2.0/24",
        args={},
    )
    store.complete_scan_run(
        denied_id, status="denied", raw_output="Authorization denied"
    )

    return store


@pytest.fixture
def client(test_config, test_system_prompt, findings_store):
    """Create test client with findings store."""
    app = create_app(test_config, test_system_prompt, findings_store=findings_store)
    return TestClient(app)


@pytest.fixture
def client_no_store(test_config, test_system_prompt):
    """Create test client without findings store."""
    app = create_app(test_config, test_system_prompt, findings_store=None)
    return TestClient(app)


class TestListFindings:
    def test_list_all_findings(self, client):
        response = client.get("/api/v1/findings")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["findings"]) == 2

    def test_filter_by_severity(self, client):
        response = client.get("/api/v1/findings?severity=high")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["findings"][0]["severity"] == "high"
        assert data["findings"][0]["title"] == "Open HTTP port"

    def test_filter_by_host(self, client):
        response = client.get("/api/v1/findings?host=192.0.2.1")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_filter_by_tool_name(self, client):
        response = client.get("/api/v1/findings?tool_name=port_scanner")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_filter_by_session_id(self, client):
        response = client.get("/api/v1/findings?session_id=test-session-1")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_filter_nonexistent_session(self, client):
        response = client.get("/api/v1/findings?session_id=nonexistent")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_limit_parameter(self, client):
        response = client.get("/api/v1/findings?limit=1")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_no_store_returns_empty(self, client_no_store):
        response = client_no_store.get("/api/v1/findings")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_finding_fields(self, client):
        response = client.get("/api/v1/findings?severity=high")
        assert response.status_code == 200
        finding = response.json()["findings"][0]
        assert finding["host"] == "192.0.2.1"
        assert finding["port"] == 80
        assert finding["protocol"] == "tcp"
        assert finding["tool_name"] == "port_scanner"
        assert finding["description"] == "Port 80 is open and serving HTTP"
        assert finding["evidence"] == "Nmap scan result"
        assert finding["remediation"] == "Close port or restrict access"


class TestExportFindings:
    def test_export_json(self, client):
        response = client.get("/api/v1/findings/export?format=json")
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]

    def test_export_csv(self, client):
        response = client.get("/api/v1/findings/export?format=csv")
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]

    def test_export_html(self, client):
        response = client.get("/api/v1/findings/export?format=html")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_export_invalid_format(self, client):
        response = client.get("/api/v1/findings/export?format=xml")
        assert response.status_code == 400

    def test_export_no_store(self, client_no_store):
        response = client_no_store.get("/api/v1/findings/export?format=json")
        assert response.status_code == 503


class TestListScanRuns:
    def test_list_all_scan_runs(self, client):
        response = client.get("/api/v1/scan-runs")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2  # completed + denied

    def test_filter_by_session_id(self, client):
        response = client.get("/api/v1/scan-runs?session_id=test-session-1")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_scan_run_fields(self, client):
        response = client.get("/api/v1/scan-runs")
        assert response.status_code == 200
        runs = response.json()["scan_runs"]
        statuses = {r["status"] for r in runs}
        assert "completed" in statuses
        assert "denied" in statuses

    def test_no_store_returns_empty(self, client_no_store):
        response = client_no_store.get("/api/v1/scan-runs")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
