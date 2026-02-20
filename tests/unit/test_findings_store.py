"""Tests for FindingsStore: CRUD, redaction, thread-safety, retention, backup."""

import json
import os
import sqlite3
import threading
from datetime import datetime, timedelta, timezone

import pytest

from tools.findings_store import (
    FindingsStore,
    FindingsStoreError,
    ScanStatus,
    Severity,
    _redact_deep,
)


@pytest.fixture
def tmp_db(tmp_path):
    """Temporary database path."""
    return str(tmp_path / "test_findings.db")


@pytest.fixture
def store(tmp_db):
    """FindingsStore with default settings."""
    return FindingsStore(db_path=tmp_db, retention_days=0)


@pytest.fixture
def strict_store(tmp_db):
    """FindingsStore with strict mode enabled."""
    return FindingsStore(db_path=tmp_db, strict=True, retention_days=0)


class TestScanStatusEnum:
    def test_running(self):
        assert ScanStatus.RUNNING == "running"

    def test_completed(self):
        assert ScanStatus.COMPLETED == "completed"

    def test_denied(self):
        assert ScanStatus.DENIED == "denied"

    def test_all_values(self):
        values = {s.value for s in ScanStatus}
        assert values == {
            "running",
            "completed",
            "failed",
            "timeout",
            "denied",
            "cancelled",
        }


class TestSeverityEnum:
    def test_all_values(self):
        values = {s.value for s in Severity}
        assert values == {"critical", "high", "medium", "low", "info"}


class TestRedaction:
    def test_redact_password_key(self):
        data = {"username": "admin", "password": "secret123"}
        result = _redact_deep(data)
        assert result["username"] == "admin"
        assert result["password"] == "[REDACTED]"

    def test_redact_ntlm_hash_key(self):
        data = {
            "ntlm_hash": "aad3b435b51404eeaad3b435b51404ee:fc525c9683e8fe067095ba2ddc971889"
        }
        result = _redact_deep(data)
        assert result["ntlm_hash"] == "[REDACTED]"

    def test_redact_api_key_in_string(self):
        text = "Connected with api_key=sk-abc123xyz"
        result = _redact_deep(text)
        assert "sk-abc123xyz" not in result
        assert "[REDACTED]" in result

    def test_redact_ntlm_hash_in_string(self):
        text = "Hash: aad3b435b51404eeaad3b435b51404ee:fc525c9683e8fe067095ba2ddc971889"
        result = _redact_deep(text)
        assert "aad3b435b51404ee" not in result
        assert "[REDACTED]" in result

    def test_redact_bearer_token(self):
        text = "Header: Bearer eyJhbGciOiJIUzI1NiJ9.payload.signature"
        result = _redact_deep(text)
        assert "eyJhbGci" not in result

    def test_redact_nested_dict(self):
        data = {"outer": {"inner": {"password": "secret"}}}
        result = _redact_deep(data)
        assert result["outer"]["inner"]["password"] == "[REDACTED]"

    def test_redact_list(self):
        data = [{"password": "a"}, {"password": "b"}]
        result = _redact_deep(data)
        assert all(item["password"] == "[REDACTED]" for item in result)

    def test_redact_preserves_non_sensitive(self):
        data = {"host": "10.0.0.1", "port": 445}
        result = _redact_deep(data)
        assert result == data

    def test_redact_none_passthrough(self):
        assert _redact_deep(None) is None

    def test_redact_int_passthrough(self):
        assert _redact_deep(42) == 42


class TestFindingsStoreInit:
    def test_creates_db_file(self, tmp_db):
        FindingsStore(db_path=tmp_db, retention_days=0)
        assert os.path.exists(tmp_db)

    def test_creates_parent_directory(self, tmp_path):
        db_path = str(tmp_path / "subdir" / "deep" / "findings.db")
        FindingsStore(db_path=db_path, retention_days=0)
        assert os.path.exists(db_path)

    def test_wal_mode_active(self, tmp_db):
        FindingsStore(db_path=tmp_db, retention_days=0)
        conn = sqlite3.connect(tmp_db)
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        conn.close()
        assert mode == "wal"

    def test_tables_created(self, tmp_db):
        FindingsStore(db_path=tmp_db, retention_days=0)
        conn = sqlite3.connect(tmp_db)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        conn.close()
        table_names = {t[0] for t in tables}
        assert "findings" in table_names
        assert "scan_runs" in table_names


class TestAddFinding:
    def test_add_and_retrieve(self, store):
        fid = store.add_finding(
            session_id="sess-1",
            severity="high",
            tool_name="smb_signing_check",
            title="SMB Signing not required",
            host="10.0.0.1",
            port=445,
        )
        assert fid is not None

        findings = store.get_findings(session_id="sess-1")
        assert len(findings) == 1
        assert findings[0].title == "SMB Signing not required"
        assert findings[0].host == "10.0.0.1"
        assert findings[0].port == 445
        assert findings[0].severity == "high"

    def test_add_with_cve_ids(self, store):
        store.add_finding(
            session_id="sess-1",
            severity="critical",
            tool_name="vuln_check",
            title="CVE Found",
            cve_ids=["CVE-2021-1234", "CVE-2022-5678"],
        )
        findings = store.get_findings()
        assert findings[0].cve_ids == ["CVE-2021-1234", "CVE-2022-5678"]

    def test_add_with_scan_run_updates_count(self, store):
        run_id = store.start_scan_run(
            session_id="sess-1", tool_name="test", target="10.0.0.1"
        )
        store.add_finding(
            scan_run_id=run_id,
            session_id="sess-1",
            severity="medium",
            tool_name="test",
            title="Finding 1",
        )
        store.add_finding(
            scan_run_id=run_id,
            session_id="sess-1",
            severity="low",
            tool_name="test",
            title="Finding 2",
        )
        runs = store.get_scan_runs(session_id="sess-1")
        assert runs[0].finding_count == 2


class TestGetFindings:
    def test_filter_by_severity(self, store):
        store.add_finding(session_id="s1", severity="high", tool_name="t1", title="A")
        store.add_finding(session_id="s1", severity="low", tool_name="t1", title="B")
        results = store.get_findings(severity="high")
        assert len(results) == 1
        assert results[0].title == "A"

    def test_filter_by_host(self, store):
        store.add_finding(
            session_id="s1", severity="info", tool_name="t1", title="A", host="10.0.0.1"
        )
        store.add_finding(
            session_id="s1", severity="info", tool_name="t1", title="B", host="10.0.0.2"
        )
        results = store.get_findings(host="10.0.0.2")
        assert len(results) == 1
        assert results[0].title == "B"

    def test_filter_by_tool_name(self, store):
        store.add_finding(
            session_id="s1", severity="info", tool_name="tool_a", title="A"
        )
        store.add_finding(
            session_id="s1", severity="info", tool_name="tool_b", title="B"
        )
        results = store.get_findings(tool_name="tool_a")
        assert len(results) == 1

    def test_limit(self, store):
        for i in range(10):
            store.add_finding(
                session_id="s1", severity="info", tool_name="t", title=f"F{i}"
            )
        results = store.get_findings(limit=3)
        assert len(results) == 3

    def test_empty_results(self, store):
        results = store.get_findings(session_id="nonexistent")
        assert results == []


class TestScanRuns:
    def test_start_and_complete(self, store):
        run_id = store.start_scan_run(
            session_id="sess-1",
            tool_name="port_scanner",
            target="10.0.0.0/24",
            args={"ports": "1-1000", "timeout": 30},
        )
        assert run_id is not None

        store.complete_scan_run(run_id, status="completed")

        runs = store.get_scan_runs(session_id="sess-1")
        assert len(runs) == 1
        assert runs[0].status == "completed"
        assert runs[0].completed_at is not None

    def test_args_redacted(self, store):
        store.start_scan_run(
            session_id="sess-1",
            tool_name="kerberoast",
            target="dc01",
            args={"username": "admin", "password": "P@ssw0rd!", "domain": "corp.local"},
        )
        runs = store.get_scan_runs(session_id="sess-1")
        args = json.loads(runs[0].args)
        assert args["username"] == "admin"  # not sensitive
        assert args["password"] == "[REDACTED]"
        assert args["domain"] == "corp.local"

    def test_raw_output_not_stored_by_default(self, store):
        run_id = store.start_scan_run(session_id="s1", tool_name="t", target="10.0.0.1")
        store.complete_scan_run(
            run_id, status="completed", raw_output="sensitive output"
        )
        runs = store.get_scan_runs(session_id="s1")
        assert runs[0].raw_output is None

    def test_raw_output_stored_when_enabled(self, tmp_db):
        store = FindingsStore(db_path=tmp_db, store_raw_output=True, retention_days=0)
        run_id = store.start_scan_run(session_id="s1", tool_name="t", target="10.0.0.1")
        store.complete_scan_run(run_id, status="completed", raw_output="some output")
        runs = store.get_scan_runs(session_id="s1")
        assert runs[0].raw_output == "some output"

    def test_raw_output_truncated(self, tmp_db):
        store = FindingsStore(
            db_path=tmp_db, store_raw_output=True, max_output_size=50, retention_days=0
        )
        run_id = store.start_scan_run(session_id="s1", tool_name="t", target="10.0.0.1")
        long_output = "A" * 200
        store.complete_scan_run(run_id, status="completed", raw_output=long_output)
        runs = store.get_scan_runs(session_id="s1")
        assert len(runs[0].raw_output) < 200
        assert "[truncated]" in runs[0].raw_output

    def test_raw_output_redacted(self, tmp_db):
        store = FindingsStore(db_path=tmp_db, store_raw_output=True, retention_days=0)
        run_id = store.start_scan_run(session_id="s1", tool_name="t", target="10.0.0.1")
        store.complete_scan_run(
            run_id,
            status="completed",
            raw_output="Found password=secret123 in config",
        )
        runs = store.get_scan_runs(session_id="s1")
        assert "secret123" not in runs[0].raw_output
        assert "[REDACTED]" in runs[0].raw_output

    def test_denied_status(self, store):
        run_id = store.start_scan_run(session_id="s1", tool_name="t", target="10.0.0.1")
        store.complete_scan_run(run_id, status="denied")
        runs = store.get_scan_runs(session_id="s1")
        assert runs[0].status == "denied"


class TestStrictMode:
    def test_default_mode_swallows_errors(self, tmp_db):
        store = FindingsStore(db_path=tmp_db, retention_days=0)
        # Force an error by closing the DB path permissions
        store.db_path = "/nonexistent/path/db.sqlite"
        # Should not raise
        result = store.add_finding(
            session_id="s1", severity="info", tool_name="t", title="test"
        )
        assert result is None

    def test_strict_mode_raises(self, tmp_db):
        store = FindingsStore(db_path=tmp_db, strict=True, retention_days=0)
        store.db_path = "/nonexistent/path/db.sqlite"
        with pytest.raises(FindingsStoreError):
            store.add_finding(
                session_id="s1", severity="info", tool_name="t", title="test"
            )


class TestThreadSafety:
    def test_concurrent_writes(self, tmp_db):
        store = FindingsStore(db_path=tmp_db, retention_days=0)
        errors = []

        def writer(thread_id):
            try:
                for i in range(20):
                    store.add_finding(
                        session_id=f"sess-{thread_id}",
                        severity="info",
                        tool_name="concurrent_test",
                        title=f"Thread {thread_id} Finding {i}",
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        findings = store.get_findings(tool_name="concurrent_test", limit=200)
        assert len(findings) == 100  # 5 threads * 20 findings


class TestRetention:
    def test_purge_expired_removes_old(self, tmp_db):
        store = FindingsStore(db_path=tmp_db, retention_days=0)
        # Add a finding
        store.add_finding(
            session_id="s1", severity="info", tool_name="t", title="old finding"
        )
        # Manually backdate it
        conn = sqlite3.connect(tmp_db)
        old_date = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
        conn.execute("UPDATE findings SET created_at = ?", (old_date,))
        conn.commit()
        conn.close()

        # Add a recent finding
        store.add_finding(
            session_id="s1", severity="info", tool_name="t", title="recent finding"
        )

        deleted = store.purge_expired(retention_days=90)
        assert deleted == 1

        remaining = store.get_findings()
        assert len(remaining) == 1
        assert remaining[0].title == "recent finding"

    def test_purge_zero_retention_disabled(self, tmp_db):
        store = FindingsStore(db_path=tmp_db, retention_days=0)
        store.add_finding(session_id="s1", severity="info", tool_name="t", title="test")
        # retention_days=0 means purge is disabled at startup
        findings = store.get_findings()
        assert len(findings) == 1


class TestBackup:
    def test_backup_creates_valid_copy(self, tmp_db, tmp_path):
        store = FindingsStore(db_path=tmp_db, retention_days=0)
        store.add_finding(
            session_id="s1", severity="high", tool_name="t", title="backup test"
        )

        backup_path = store.backup(backup_dir=str(tmp_path))
        assert backup_path is not None
        assert os.path.exists(backup_path)

        # Verify backup is valid SQLite with data
        conn = sqlite3.connect(backup_path)
        count = conn.execute("SELECT COUNT(*) FROM findings").fetchone()[0]
        conn.close()
        assert count == 1
