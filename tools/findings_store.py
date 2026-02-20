"""SQLite-based Findings Database for security scan results.

Thread-safe (WAL mode), credential redaction, configurable retention.
DB errors NEVER block tool execution (default). Strict mode available
for compliance contexts.
"""

import json
import logging
import re
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FindingsStoreError(Exception):
    """Raised in strict mode when DB operations fail."""

    pass


class ScanStatus(str, Enum):
    """Scan run status values."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    DENIED = "denied"
    CANCELLED = "cancelled"


class Severity(str, Enum):
    """Finding severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Finding:
    """A security finding from a tool execution."""

    id: str
    scan_run_id: Optional[str]
    session_id: str
    host: Optional[str]
    port: Optional[int]
    protocol: str
    severity: str
    tool_name: str
    title: str
    description: Optional[str]
    evidence: Optional[str]
    remediation: Optional[str]
    cve_ids: Optional[List[str]]
    created_at: str


@dataclass
class ScanRun:
    """A record of a tool execution."""

    id: str
    session_id: str
    tool_name: str
    target: str
    args: Optional[str]
    started_at: str
    completed_at: Optional[str]
    status: str
    raw_output: Optional[str]
    finding_count: int


# --- Credential Redaction ---

REDACT_KEYS = {
    "password",
    "hash",
    "ntlm_hash",
    "api_key",
    "secret",
    "credential",
    "ticket",
    "key",
    "token",
    "auth",
}

_CREDENTIAL_PATTERNS = re.compile(
    r"|".join(
        [
            r"[a-fA-F0-9]{32}:[a-fA-F0-9]{32}",  # NTLM LM:NT hash
            r"password\s*[=:]\s*\S+",  # password=... or password: ...
            r"api_key\s*[=:]\s*\S+",  # api_key=...
            r"Bearer\s+[A-Za-z0-9\-._~+/]+=*",  # Bearer tokens
            r"Authorization:\s*\S+(?:\s+\S+)*",  # Authorization headers (multi-word)
            r"secret\s*[=:]\s*\S+",  # secret=...
            r"token\s*[=:]\s*\S+",  # token=...
        ]
    ),
    re.IGNORECASE,
)


def _redact_deep(obj: Any) -> Any:
    """Recursively redact credentials from dicts, lists, and strings."""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if isinstance(k, str) and k.lower() in REDACT_KEYS:
                result[k] = "[REDACTED]"
            else:
                result[k] = _redact_deep(v)
        return result
    elif isinstance(obj, list):
        return [_redact_deep(item) for item in obj]
    elif isinstance(obj, str):
        return _CREDENTIAL_PATTERNS.sub("[REDACTED]", obj)
    return obj


# --- Schema ---

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS scan_runs (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    target TEXT NOT NULL,
    args TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL DEFAULT 'running'
        CHECK (status IN ('running','completed','failed','timeout','denied','cancelled')),
    raw_output TEXT,
    finding_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS findings (
    id TEXT PRIMARY KEY,
    scan_run_id TEXT REFERENCES scan_runs(id),
    session_id TEXT NOT NULL,
    host TEXT,
    port INTEGER,
    protocol TEXT DEFAULT 'tcp',
    severity TEXT NOT NULL DEFAULT 'info'
        CHECK (severity IN ('critical','high','medium','low','info')),
    tool_name TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    evidence TEXT,
    remediation TEXT,
    cve_ids TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_findings_session ON findings(session_id);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(severity);
CREATE INDEX IF NOT EXISTS idx_findings_tool ON findings(tool_name);
CREATE INDEX IF NOT EXISTS idx_findings_host ON findings(host);
CREATE INDEX IF NOT EXISTS idx_scan_runs_session ON scan_runs(session_id);
"""


class FindingsStore:
    """SQLite-based storage for security findings and scan runs.

    Thread-safe via WAL mode + per-instance lock.
    DB errors are logged but never block tool execution (default).
    Set strict=True for fail-closed behavior in compliance contexts.
    """

    def __init__(
        self,
        db_path: str = "data/findings.db",
        store_raw_output: bool = False,
        max_output_size: int = 10000,
        strict: bool = False,
        retention_days: int = 90,
    ):
        self.db_path = db_path
        self.store_raw_output = store_raw_output
        self.max_output_size = max_output_size
        self.strict = strict
        self.retention_days = retention_days
        self._lock = threading.Lock()

        # Ensure parent directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

        # Lazy retention cleanup on startup
        if self.retention_days > 0:
            try:
                self.purge_expired(self.retention_days)
            except Exception as e:
                logger.warning(f"Retention cleanup failed: {e}")

    def _get_connection(self) -> sqlite3.Connection:
        """Create a new connection with WAL mode and busy timeout."""
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = self._get_connection()
        try:
            conn.executescript(_SCHEMA_SQL)
            conn.commit()
        finally:
            conn.close()

    def _handle_error(self, operation: str, error: Exception) -> None:
        """Handle DB errors: raise in strict mode, log warning otherwise."""
        if self.strict:
            raise FindingsStoreError(
                f"DB operation '{operation}' failed: {error}"
            ) from error
        logger.warning(f"FindingsStore.{operation} failed: {error}")

    def add_finding(
        self,
        scan_run_id: Optional[str] = None,
        session_id: str = "",
        severity: str = "info",
        tool_name: str = "",
        title: str = "",
        host: Optional[str] = None,
        port: Optional[int] = None,
        protocol: str = "tcp",
        description: Optional[str] = None,
        evidence: Optional[str] = None,
        remediation: Optional[str] = None,
        cve_ids: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Add a security finding. Returns finding ID or None on failure."""
        finding_id = str(uuid.uuid4())
        cve_json = json.dumps(cve_ids) if cve_ids else None

        try:
            with self._lock:
                conn = self._get_connection()
                try:
                    conn.execute(
                        """INSERT INTO findings
                        (id, scan_run_id, session_id, host, port, protocol,
                         severity, tool_name, title, description, evidence,
                         remediation, cve_ids)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            finding_id,
                            scan_run_id,
                            session_id,
                            host,
                            port,
                            protocol,
                            severity,
                            tool_name,
                            title,
                            description,
                            evidence,
                            remediation,
                            cve_json,
                        ),
                    )
                    # Update finding_count on scan_run
                    if scan_run_id:
                        conn.execute(
                            """UPDATE scan_runs SET finding_count = finding_count + 1
                            WHERE id = ?""",
                            (scan_run_id,),
                        )
                    conn.commit()
                    return finding_id
                finally:
                    conn.close()
        except Exception as e:
            self._handle_error("add_finding", e)
            return None

    def get_findings(
        self,
        session_id: Optional[str] = None,
        severity: Optional[str] = None,
        host: Optional[str] = None,
        tool_name: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Finding]:
        """Query findings with optional filters."""
        conditions = []
        params: list = []

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        if severity:
            conditions.append("severity = ?")
            params.append(severity)
        if host:
            conditions.append("host = ?")
            params.append(host)
        if tool_name:
            conditions.append("tool_name = ?")
            params.append(tool_name)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"SELECT * FROM findings {where} ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        try:
            conn = self._get_connection()
            try:
                rows = conn.execute(query, params).fetchall()
                return [
                    Finding(
                        id=row["id"],
                        scan_run_id=row["scan_run_id"],
                        session_id=row["session_id"],
                        host=row["host"],
                        port=row["port"],
                        protocol=row["protocol"],
                        severity=row["severity"],
                        tool_name=row["tool_name"],
                        title=row["title"],
                        description=row["description"],
                        evidence=row["evidence"],
                        remediation=row["remediation"],
                        cve_ids=json.loads(row["cve_ids"]) if row["cve_ids"] else None,
                        created_at=row["created_at"],
                    )
                    for row in rows
                ]
            finally:
                conn.close()
        except Exception as e:
            self._handle_error("get_findings", e)
            return []

    def start_scan_run(
        self,
        session_id: str,
        tool_name: str,
        target: str,
        args: Optional[Dict] = None,
    ) -> Optional[str]:
        """Record start of a scan run. Args are redacted before insert.
        Returns scan_run ID or None on failure.
        """
        run_id = str(uuid.uuid4())
        redacted_args = json.dumps(_redact_deep(args)) if args else None
        started_at = datetime.now(timezone.utc).isoformat()

        try:
            with self._lock:
                conn = self._get_connection()
                try:
                    conn.execute(
                        """INSERT INTO scan_runs
                        (id, session_id, tool_name, target, args, started_at, status)
                        VALUES (?, ?, ?, ?, ?, ?, 'running')""",
                        (
                            run_id,
                            session_id,
                            tool_name,
                            target,
                            redacted_args,
                            started_at,
                        ),
                    )
                    conn.commit()
                    return run_id
                finally:
                    conn.close()
        except Exception as e:
            self._handle_error("start_scan_run", e)
            return None

    def complete_scan_run(
        self,
        scan_run_id: str,
        status: str,
        raw_output: Optional[str] = None,
    ) -> None:
        """Record completion of a scan run."""
        completed_at = datetime.now(timezone.utc).isoformat()

        # Handle raw_output: redact, truncate, or discard
        stored_output = None
        if self.store_raw_output and raw_output:
            redacted = _redact_deep(raw_output)
            if isinstance(redacted, str) and len(redacted) > self.max_output_size:
                redacted = redacted[: self.max_output_size] + "\n... [truncated]"
            stored_output = redacted

        try:
            with self._lock:
                conn = self._get_connection()
                try:
                    conn.execute(
                        """UPDATE scan_runs
                        SET completed_at = ?, status = ?, raw_output = ?
                        WHERE id = ?""",
                        (completed_at, status, stored_output, scan_run_id),
                    )
                    conn.commit()
                finally:
                    conn.close()
        except Exception as e:
            self._handle_error("complete_scan_run", e)

    def get_scan_runs(
        self,
        session_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[ScanRun]:
        """Query scan runs with optional session filter."""
        if session_id:
            query = "SELECT * FROM scan_runs WHERE session_id = ? ORDER BY started_at DESC LIMIT ?"
            params = [session_id, limit]
        else:
            query = "SELECT * FROM scan_runs ORDER BY started_at DESC LIMIT ?"
            params = [limit]

        try:
            conn = self._get_connection()
            try:
                rows = conn.execute(query, params).fetchall()
                return [
                    ScanRun(
                        id=row["id"],
                        session_id=row["session_id"],
                        tool_name=row["tool_name"],
                        target=row["target"],
                        args=row["args"],
                        started_at=row["started_at"],
                        completed_at=row["completed_at"],
                        status=row["status"],
                        raw_output=row["raw_output"],
                        finding_count=row["finding_count"],
                    )
                    for row in rows
                ]
            finally:
                conn.close()
        except Exception as e:
            self._handle_error("get_scan_runs", e)
            return []

    def purge_expired(self, retention_days: int) -> int:
        """Delete findings older than retention_days. Returns count deleted."""
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=retention_days)
        ).isoformat()

        try:
            with self._lock:
                conn = self._get_connection()
                try:
                    cursor = conn.execute(
                        "DELETE FROM findings WHERE created_at < ?", (cutoff,)
                    )
                    deleted = cursor.rowcount
                    conn.commit()
                    if deleted > 0:
                        logger.info(
                            f"Purged {deleted} findings older than {retention_days} days"
                        )
                    return deleted
                finally:
                    conn.close()
        except Exception as e:
            self._handle_error("purge_expired", e)
            return 0

    def backup(self, backup_dir: Optional[str] = None) -> Optional[str]:
        """Create a timestamped backup of the database.
        Returns backup path or None on failure.
        """
        if backup_dir is None:
            backup_dir = str(Path(self.db_path).parent)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        db_name = Path(self.db_path).stem
        backup_path = str(Path(backup_dir) / f"{db_name}_backup_{timestamp}.db")

        try:
            with self._lock:
                conn = self._get_connection()
                try:
                    backup_conn = sqlite3.connect(backup_path)
                    conn.backup(backup_conn)
                    backup_conn.close()
                    logger.info(f"Database backed up to {backup_path}")
                    return backup_path
                finally:
                    conn.close()
        except Exception as e:
            self._handle_error("backup", e)
            return None

    def close(self) -> None:
        """No persistent connections to close (connections are per-operation)."""
        pass
