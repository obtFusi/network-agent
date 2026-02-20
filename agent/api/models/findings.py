"""Pydantic models for Findings API responses."""

from typing import Optional

from pydantic import BaseModel, Field


class FindingResponse(BaseModel):
    """Response model for a single finding."""

    id: str = Field(..., description="Unique finding identifier")
    scan_run_id: Optional[str] = Field(None, description="Associated scan run ID")
    session_id: str = Field(..., description="Session that produced this finding")
    host: Optional[str] = Field(None, description="Affected host IP/hostname")
    port: Optional[int] = Field(None, description="Affected port number")
    protocol: str = Field("tcp", description="Protocol (tcp/udp)")
    severity: str = Field(
        ..., description="Severity level (critical/high/medium/low/info)"
    )
    tool_name: str = Field(..., description="Tool that produced this finding")
    title: str = Field(..., description="Finding title")
    description: Optional[str] = Field(None, description="Detailed description")
    evidence: Optional[str] = Field(None, description="Evidence supporting the finding")
    remediation: Optional[str] = Field(None, description="Remediation recommendation")
    cve_ids: Optional[str] = Field(None, description="Associated CVE IDs (JSON array)")
    created_at: str = Field(..., description="Creation timestamp")


class FindingsListResponse(BaseModel):
    """Response model for listing findings."""

    findings: list[FindingResponse] = Field(
        default_factory=list, description="List of findings"
    )
    total: int = Field(..., description="Total number of findings returned")


class ScanRunResponse(BaseModel):
    """Response model for a single scan run."""

    id: str = Field(..., description="Unique scan run identifier")
    session_id: str = Field(..., description="Session ID")
    tool_name: str = Field(..., description="Tool name")
    target: str = Field(..., description="Scan target")
    args: Optional[str] = Field(None, description="Tool arguments (redacted)")
    started_at: str = Field(..., description="Start timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")
    status: str = Field(
        ...,
        description="Run status (running/completed/failed/denied/cancelled/timeout)",
    )
    finding_count: int = Field(0, description="Number of findings from this run")


class ScanRunsListResponse(BaseModel):
    """Response model for listing scan runs."""

    scan_runs: list[ScanRunResponse] = Field(
        default_factory=list, description="List of scan runs"
    )
    total: int = Field(..., description="Total number of scan runs returned")
