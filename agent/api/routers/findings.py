"""Findings API router for querying and exporting security findings."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, Response

from agent.api.models.findings import (
    FindingResponse,
    FindingsListResponse,
    ScanRunResponse,
    ScanRunsListResponse,
)
from tools.findings_store import FindingsStore

router = APIRouter(tags=["findings"])


def _get_findings_store(request: Request) -> Optional[FindingsStore]:
    """Get findings store from app state."""
    return getattr(request.app.state, "findings_store", None)


@router.get("/findings", response_model=FindingsListResponse)
async def list_findings(
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    severity: Optional[str] = Query(
        None, description="Filter by severity (critical/high/medium/low/info)"
    ),
    host: Optional[str] = Query(None, description="Filter by host IP/hostname"),
    tool_name: Optional[str] = Query(None, description="Filter by tool name"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum results"),
    store: Optional[FindingsStore] = Depends(_get_findings_store),
):
    """List findings with optional filters."""
    if store is None:
        return FindingsListResponse(findings=[], total=0)

    findings = store.get_findings(
        session_id=session_id,
        severity=severity,
        host=host,
        tool_name=tool_name,
        limit=limit,
    )

    return FindingsListResponse(
        findings=[
            FindingResponse(
                id=f.id,
                scan_run_id=f.scan_run_id,
                session_id=f.session_id,
                host=f.host,
                port=f.port,
                protocol=f.protocol,
                severity=f.severity,
                tool_name=f.tool_name,
                title=f.title,
                description=f.description,
                evidence=f.evidence,
                remediation=f.remediation,
                cve_ids=str(f.cve_ids) if f.cve_ids else None,
                created_at=f.created_at,
            )
            for f in findings
        ],
        total=len(findings),
    )


@router.get("/findings/export")
async def export_findings(
    format: str = Query("json", description="Export format (json/csv/html)"),
    store: Optional[FindingsStore] = Depends(_get_findings_store),
):
    """Export findings report in specified format."""
    if store is None:
        return Response(content="Findings database not configured", status_code=503)

    if format not in ("json", "csv", "html"):
        return Response(content=f"Unsupported format: {format}", status_code=400)

    from tools.findings_export import export_csv, export_html, export_json

    # Export to temporary path and stream back
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        exporters = {"json": export_json, "csv": export_csv, "html": export_html}
        result_path = exporters[format](store, tmp_path)

        media_types = {
            "json": "application/json",
            "csv": "text/csv",
            "html": "text/html",
        }

        with open(result_path, "rb") as f:
            content = f.read()

        return Response(
            content=content,
            media_type=media_types[format],
            headers={
                "Content-Disposition": f"attachment; filename=findings_report.{format}"
            },
        )
    finally:
        import os

        try:
            os.unlink(tmp_path)
            # Also remove the .sha256 sidecar if it exists
            sha_path = tmp_path + ".sha256"
            if os.path.exists(sha_path):
                os.unlink(sha_path)
        except OSError:
            pass


@router.get("/scan-runs", response_model=ScanRunsListResponse)
async def list_scan_runs(
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    limit: int = Query(100, ge=1, le=10000, description="Maximum results"),
    store: Optional[FindingsStore] = Depends(_get_findings_store),
):
    """List scan runs with optional session filter."""
    if store is None:
        return ScanRunsListResponse(scan_runs=[], total=0)

    runs = store.get_scan_runs(session_id=session_id, limit=limit)

    return ScanRunsListResponse(
        scan_runs=[
            ScanRunResponse(
                id=r.id,
                session_id=r.session_id,
                tool_name=r.tool_name,
                target=r.target,
                args=r.args,
                started_at=r.started_at,
                completed_at=r.completed_at,
                status=r.status,
                finding_count=r.finding_count,
            )
            for r in runs
        ],
        total=len(runs),
    )
