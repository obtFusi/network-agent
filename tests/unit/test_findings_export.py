"""Tests for findings export: JSON, CSV, HTML with integrity verification."""

import csv
import hashlib
import json
import os

import pytest

from tools.findings_export import export_csv, export_html, export_json
from tools.findings_store import FindingsStore


@pytest.fixture
def store(tmp_path):
    """FindingsStore with sample data."""
    db_path = str(tmp_path / "export_test.db")
    s = FindingsStore(db_path=db_path, retention_days=0)

    # Add sample findings
    run_id = s.start_scan_run(
        session_id="export-session",
        tool_name="smb_signing_check",
        target="10.0.0.0/24",
    )
    s.add_finding(
        scan_run_id=run_id,
        session_id="export-session",
        severity="high",
        tool_name="smb_signing_check",
        title="SMB Signing not required",
        host="10.0.0.1",
        port=445,
        description="SMB signing is not enforced",
        remediation="Enable SMB signing via GPO",
        cve_ids=["CVE-2021-1234"],
    )
    s.add_finding(
        scan_run_id=run_id,
        session_id="export-session",
        severity="critical",
        tool_name="kerberoast",
        title="Kerberoastable SPN found",
        host="10.0.0.5",
        description="Service account with weak SPN",
    )
    s.add_finding(
        session_id="export-session",
        severity="info",
        tool_name="ping_sweep",
        title="Host alive",
        host="10.0.0.1",
    )
    s.complete_scan_run(run_id, status="completed")

    return s


class TestJSONExport:
    def test_valid_json(self, store, tmp_path):
        path = str(tmp_path / "report.json")
        export_json(store, path)

        with open(path) as f:
            data = json.load(f)

        assert "report" in data
        assert "findings" in data
        assert "scan_runs" in data

    def test_severity_breakdown(self, store, tmp_path):
        path = str(tmp_path / "report.json")
        export_json(store, path)

        with open(path) as f:
            data = json.load(f)

        breakdown = data["report"]["severity_breakdown"]
        assert breakdown["critical"] == 1
        assert breakdown["high"] == 1
        assert breakdown["info"] == 1
        assert data["report"]["total_findings"] == 3

    def test_sha256_sidecar(self, store, tmp_path):
        path = str(tmp_path / "report.json")
        export_json(store, path)

        sidecar = path + ".sha256"
        assert os.path.exists(sidecar)

        with open(path, "rb") as f:
            expected_hash = hashlib.sha256(f.read()).hexdigest()
        with open(sidecar) as f:
            actual = f.read().strip()

        assert expected_hash in actual

    def test_filter_by_severity(self, store, tmp_path):
        path = str(tmp_path / "report.json")
        export_json(store, path, severity="critical")

        with open(path) as f:
            data = json.load(f)

        assert len(data["findings"]) == 1
        assert data["findings"][0]["severity"] == "critical"

    def test_cve_ids_preserved(self, store, tmp_path):
        path = str(tmp_path / "report.json")
        export_json(store, path)

        with open(path) as f:
            data = json.load(f)

        smb_finding = [
            f for f in data["findings"] if f["tool_name"] == "smb_signing_check"
        ][0]
        assert smb_finding["cve_ids"] == ["CVE-2021-1234"]


class TestCSVExport:
    def test_valid_csv(self, store, tmp_path):
        path = str(tmp_path / "report.csv")
        export_csv(store, path)

        with open(path) as f:
            reader = csv.reader(f)
            rows = list(reader)

        # Header + 3 findings
        assert len(rows) == 4
        assert rows[0][0] == "id"
        assert "severity" in rows[0]

    def test_sha256_sidecar(self, store, tmp_path):
        path = str(tmp_path / "report.csv")
        export_csv(store, path)
        assert os.path.exists(path + ".sha256")

    def test_filter_by_host(self, store, tmp_path):
        path = str(tmp_path / "report.csv")
        export_csv(store, path, host="10.0.0.5")

        with open(path) as f:
            reader = csv.reader(f)
            rows = list(reader)

        assert len(rows) == 2  # header + 1 finding


class TestHTMLExport:
    def test_valid_html(self, store, tmp_path):
        path = str(tmp_path / "report.html")
        export_html(store, path)

        with open(path) as f:
            content = f.read()

        assert "<!DOCTYPE html>" in content
        assert "Security Findings Report" in content

    def test_xss_escaped(self, store, tmp_path):
        # Add a finding with XSS payload
        store.add_finding(
            session_id="export-session",
            severity="info",
            tool_name="xss_test",
            title='<script>alert("xss")</script>',
            description='<img onerror="alert(1)" src=x>',
            host="10.0.0.1",
        )

        path = str(tmp_path / "report.html")
        export_html(store, path)

        with open(path) as f:
            content = f.read()

        # Raw XSS must NOT appear
        assert "<script>" not in content
        assert 'onerror="' not in content
        # Escaped versions should appear
        assert "&lt;script&gt;" in content

    def test_severity_cards(self, store, tmp_path):
        path = str(tmp_path / "report.html")
        export_html(store, path)

        with open(path) as f:
            content = f.read()

        assert "Critical" in content
        assert "High" in content

    def test_sha256_sidecar(self, store, tmp_path):
        path = str(tmp_path / "report.html")
        export_html(store, path)
        assert os.path.exists(path + ".sha256")

    def test_sha256_content_matches(self, store, tmp_path):
        path = str(tmp_path / "report.html")
        export_html(store, path)

        with open(path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        with open(path + ".sha256") as f:
            sidecar_content = f.read().strip()

        assert file_hash in sidecar_content
