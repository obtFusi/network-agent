"""Export functions for Findings Database.

Supports JSON, CSV, and HTML export with severity breakdown.
Each export generates a .sha256 sidecar file for integrity verification.
"""

import csv
import hashlib
import html
import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from tools.findings_store import Finding, FindingsStore

logger = logging.getLogger(__name__)


def _write_sha256_sidecar(file_path: str, content: bytes) -> str:
    """Generate .sha256 sidecar file for integrity verification."""
    sha256_hash = hashlib.sha256(content).hexdigest()
    sidecar_path = f"{file_path}.sha256"
    filename = Path(file_path).name
    with open(sidecar_path, "w") as f:
        f.write(f"{sha256_hash}  {filename}\n")
    return sidecar_path


def _severity_breakdown(findings: List[Finding]) -> dict:
    """Count findings per severity level."""
    breakdown = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for f in findings:
        if f.severity in breakdown:
            breakdown[f.severity] += 1
    return breakdown


def export_json(
    store: FindingsStore,
    output_path: str,
    session_id: Optional[str] = None,
    severity: Optional[str] = None,
    host: Optional[str] = None,
    tool_name: Optional[str] = None,
) -> str:
    """Export findings as JSON with severity breakdown.

    Returns path to exported file.
    """
    findings = store.get_findings(
        session_id=session_id,
        severity=severity,
        host=host,
        tool_name=tool_name,
    )
    scan_runs = store.get_scan_runs(session_id=session_id)

    report = {
        "report": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_findings": len(findings),
            "severity_breakdown": _severity_breakdown(findings),
        },
        "findings": [
            {
                "id": f.id,
                "scan_run_id": f.scan_run_id,
                "session_id": f.session_id,
                "host": f.host,
                "port": f.port,
                "protocol": f.protocol,
                "severity": f.severity,
                "tool_name": f.tool_name,
                "title": f.title,
                "description": f.description,
                "evidence": f.evidence,
                "remediation": f.remediation,
                "cve_ids": f.cve_ids,
                "created_at": f.created_at,
            }
            for f in findings
        ],
        "scan_runs": [
            {
                "id": r.id,
                "session_id": r.session_id,
                "tool_name": r.tool_name,
                "target": r.target,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
                "status": r.status,
                "finding_count": r.finding_count,
            }
            for r in scan_runs
        ],
    }

    content = json.dumps(report, indent=2).encode("utf-8")
    with open(output_path, "wb") as f:
        f.write(content)

    _write_sha256_sidecar(output_path, content)
    return output_path


def export_csv(
    store: FindingsStore,
    output_path: str,
    session_id: Optional[str] = None,
    severity: Optional[str] = None,
    host: Optional[str] = None,
    tool_name: Optional[str] = None,
) -> str:
    """Export findings as CSV for spreadsheet import.

    Returns path to exported file.
    """
    findings = store.get_findings(
        session_id=session_id,
        severity=severity,
        host=host,
        tool_name=tool_name,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "severity",
            "tool_name",
            "title",
            "host",
            "port",
            "protocol",
            "description",
            "evidence",
            "remediation",
            "cve_ids",
            "created_at",
        ]
    )

    for f in findings:
        writer.writerow(
            [
                f.id,
                f.severity,
                f.tool_name,
                f.title,
                f.host,
                f.port,
                f.protocol,
                f.description or "",
                f.evidence or "",
                f.remediation or "",
                ",".join(f.cve_ids) if f.cve_ids else "",
                f.created_at,
            ]
        )

    content = output.getvalue().encode("utf-8")
    with open(output_path, "wb") as f:
        f.write(content)

    _write_sha256_sidecar(output_path, content)
    return output_path


def export_html(
    store: FindingsStore,
    output_path: str,
    session_id: Optional[str] = None,
    severity: Optional[str] = None,
    host: Optional[str] = None,
    tool_name: Optional[str] = None,
) -> str:
    """Export findings as HTML report with XSS-safe escaping.

    Returns path to exported file.
    """
    findings = store.get_findings(
        session_id=session_id,
        severity=severity,
        host=host,
        tool_name=tool_name,
    )
    breakdown = _severity_breakdown(findings)

    # XSS-safe: all user data escaped via html.escape()
    e = html.escape

    severity_colors = {
        "critical": "#dc3545",
        "high": "#fd7e14",
        "medium": "#ffc107",
        "low": "#17a2b8",
        "info": "#6c757d",
    }

    findings_rows = ""
    for f in findings:
        color = severity_colors.get(f.severity, "#6c757d")
        cve_str = ", ".join(f.cve_ids) if f.cve_ids else ""
        findings_rows += f"""<tr>
<td><span style="background:{color};color:white;padding:2px 6px;border-radius:3px;">{e(f.severity)}</span></td>
<td>{e(f.tool_name)}</td>
<td>{e(f.title)}</td>
<td>{e(f.host or "")}</td>
<td>{e(str(f.port) if f.port else "")}</td>
<td>{e(f.description or "")}</td>
<td>{e(f.evidence or "")}</td>
<td>{e(f.remediation or "")}</td>
<td>{e(cve_str)}</td>
<td>{e(f.created_at)}</td>
</tr>
"""

    report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Security Findings Report</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 20px; }}
h1 {{ color: #333; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 14px; }}
th {{ background: #f8f9fa; font-weight: bold; }}
tr:nth-child(even) {{ background: #f9f9f9; }}
.summary {{ display: flex; gap: 20px; margin: 20px 0; }}
.summary-card {{ padding: 15px; border-radius: 5px; color: white; min-width: 120px; text-align: center; }}
</style>
</head>
<body>
<h1>Security Findings Report</h1>
<p>Generated: {e(datetime.now(timezone.utc).isoformat())}</p>

<h2>Executive Summary</h2>
<div class="summary">
<div class="summary-card" style="background:#dc3545;">
<div style="font-size:24px;font-weight:bold;">{breakdown["critical"]}</div>
<div>Critical</div>
</div>
<div class="summary-card" style="background:#fd7e14;">
<div style="font-size:24px;font-weight:bold;">{breakdown["high"]}</div>
<div>High</div>
</div>
<div class="summary-card" style="background:#ffc107;color:#333;">
<div style="font-size:24px;font-weight:bold;">{breakdown["medium"]}</div>
<div>Medium</div>
</div>
<div class="summary-card" style="background:#17a2b8;">
<div style="font-size:24px;font-weight:bold;">{breakdown["low"]}</div>
<div>Low</div>
</div>
<div class="summary-card" style="background:#6c757d;">
<div style="font-size:24px;font-weight:bold;">{breakdown["info"]}</div>
<div>Info</div>
</div>
</div>
<p><strong>Total Findings:</strong> {len(findings)}</p>

<h2>Findings</h2>
<table>
<thead>
<tr>
<th>Severity</th><th>Tool</th><th>Title</th><th>Host</th><th>Port</th>
<th>Description</th><th>Evidence</th><th>Remediation</th><th>CVEs</th><th>Date</th>
</tr>
</thead>
<tbody>
{findings_rows}
</tbody>
</table>
</body>
</html>"""

    content = report_html.encode("utf-8")
    with open(output_path, "wb") as f:
        f.write(content)

    _write_sha256_sidecar(output_path, content)
    return output_path
