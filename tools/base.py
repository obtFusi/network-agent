import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Structured result from tool execution.

    Status values match ScanStatus enum: completed, failed, denied, cancelled, timeout.
    """

    status: str  # completed, failed, denied, cancelled, timeout
    message: str
    error_type: Optional[str] = None  # validation, dependency, runtime, auth


class BaseTool(ABC):
    """Base class for all tools.

    Subclasses override authorization_level, category, and target_fields
    to participate in the authorization and scope enforcement system.
    """

    def __init__(self):
        # Findings integration (set by agent core when FindingsStore is active)
        self._findings_store = None
        self._current_scan_run = None
        self._current_session_id = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name for LLM."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for LLM."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """JSON Schema for tool parameters."""
        pass

    @property
    def authorization_level(self) -> str:
        """Required authorization level: passive, active, or destructive."""
        return "passive"

    @property
    def category(self) -> str:
        """Attack-chain category: recon, poison, enum, harvest, lateral, persist, compliance."""
        return "recon"

    @property
    def target_fields(self) -> List[str]:
        """Parameter names containing scope-relevant targets.

        ScopeConfig validates ALL listed parameters against the allowlist.
        Override for tools with multiple or non-standard target parameters.

        Examples:
            - Default: ["target"]
            - Ping sweep: ["target", "network"]
            - Sniffer: ["interface"]
            - AD tools: ["target", "domain"]
        """
        return ["target"]

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Execute tool, returns string."""
        pass

    def report_finding(
        self,
        severity: str,
        title: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        protocol: str = "tcp",
        description: Optional[str] = None,
        evidence: Optional[str] = None,
        remediation: Optional[str] = None,
        cve_ids: Optional[List[str]] = None,
    ) -> None:
        """Report a security finding to the FindingsStore.

        No-op if FindingsStore is not configured. ALL exceptions caught
        to ensure findings never block tool execution.
        """
        if self._findings_store is None:
            return

        try:
            self._findings_store.add_finding(
                scan_run_id=self._current_scan_run,
                session_id=self._current_session_id or "",
                severity=severity,
                tool_name=self.name,
                title=title,
                host=host,
                port=port,
                protocol=protocol,
                description=description,
                evidence=evidence,
                remediation=remediation,
                cve_ids=cve_ids,
            )
        except Exception as e:
            logger.warning(f"Failed to report finding: {e}")

    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI Function Calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
