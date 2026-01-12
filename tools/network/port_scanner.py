"""Port Scanner Tool - TCP port scanning with nmap backend."""

import subprocess
from typing import List, Optional
from tools.base import BaseTool
from tools.validation import (
    resolve_and_validate,
    require_nmap,
    validate_port_list,
    count_ports,
)
from tools.config import get_scan_config


class PortScannerTool(BaseTool):
    # Valid timing templates (T0=paranoid to T5=insane)
    TIMING_TEMPLATES = ["T0", "T1", "T2", "T3", "T4", "T5"]

    def __init__(self):
        super().__init__()
        self._config = get_scan_config()

    @property
    def name(self) -> str:
        return "port_scanner"

    @property
    def description(self) -> str:
        return (
            "Scans TCP ports on target hosts. Supports single IPs, hostnames, "
            "or networks (max /24). Use port lists (22,80,443) or ranges (1-1000). "
            "Max 1000 ports per scan. Private networks only."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "IP address, hostname, or CIDR network (max /24)",
                },
                "ports": {
                    "type": "string",
                    "description": "Port list (22,80,443) or range (1-1000). Default: top 100 ports",
                },
                "timing": {
                    "type": "string",
                    "enum": self.TIMING_TEMPLATES,
                    "description": "Scan speed: T0 (slowest) to T5 (fastest). Default: T3",
                },
                "skip_discovery": {
                    "type": "boolean",
                    "description": "Skip host discovery (-Pn). Use for hosts that block ping.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds. Default: from config or 120",
                },
            },
            "required": ["target"],
        }

    @property
    def max_hosts(self) -> int:
        """Use portscan limit (256 = /24), not discovery limit."""
        return self._config.max_hosts_portscan

    @property
    def exclude_list(self) -> List[str]:
        return self._config.exclude_ips

    @property
    def default_timeout(self) -> int:
        return self._config.timeout

    @property
    def default_ports(self) -> Optional[str]:
        """Get default ports from config, or None for --top-ports."""
        return self._config.tcp_ports

    def _validate_config_ports(self, ports: str) -> tuple[bool, str]:
        """Validate config ports, return (valid, warning_if_invalid)."""
        valid, error, _ = validate_port_list(ports)
        if not valid:
            return (
                False,
                f"Warning: Invalid config ports ({error}), using --top-ports 100",
            )
        return True, ""

    def execute(
        self,
        target: str,
        ports: str = None,
        timing: str = "T3",
        skip_discovery: bool = False,
        timeout: int = None,
    ) -> str:
        """Execute port scan."""
        warnings: List[str] = []

        # === TYPE GUARDS (LLM can send wrong types!) ===
        if not isinstance(target, str):
            return (
                f"Validation error: target must be string, got {type(target).__name__}"
            )
        if ports is not None and not isinstance(ports, str):
            return f"Validation error: ports must be string, got {type(ports).__name__}"
        if not isinstance(timing, str):
            return (
                f"Validation error: timing must be string, got {type(timing).__name__}"
            )
        # skip_discovery: bool check (bool is int subclass, but we accept both)
        if not isinstance(skip_discovery, bool):
            return f"Validation error: skip_discovery must be boolean, got {type(skip_discovery).__name__}"
        # timeout: int check (exclude bool!)
        if timeout is not None:
            if type(timeout) is not int:
                return f"Validation error: timeout must be integer, got {type(timeout).__name__}"
            if timeout < 1:
                return f"Validation error: timeout must be >= 1, got {timeout}"

        # === CONFIG CHECK ===
        if config_error := self._config.get_error():
            return f"Validation error: {config_error}"

        # === NMAP CHECK ===
        nmap_ok, nmap_error = require_nmap()
        if not nmap_ok:
            return nmap_error

        # === TIMING VALIDATION ===
        timing = timing.upper()
        if timing not in self.TIMING_TEMPLATES:
            return f"Validation error: Invalid timing '{timing}'. Valid: {', '.join(self.TIMING_TEMPLATES)}"

        # === TARGET VALIDATION ===
        valid, error, targets = resolve_and_validate(
            target,
            allow_public=False,
            max_hosts=self.max_hosts,
            exclude_list=self.exclude_list,
        )
        if not valid:
            return error

        # Order-preserving dedup
        targets = list(dict.fromkeys(targets))

        # === PORT VALIDATION ===
        use_top_ports = False
        if ports is None:
            # Try config default ports
            config_ports = self.default_ports
            if config_ports:
                valid, warning = self._validate_config_ports(config_ports)
                if valid:
                    ports = config_ports
                else:
                    warnings.append(warning)
                    use_top_ports = True
            else:
                use_top_ports = True
        else:
            # Validate user-provided ports
            valid, error, normalized = validate_port_list(ports)
            if not valid:
                return error
            ports = normalized

        # === WARNINGS ===
        # Warn if -Pn with network range (can be slow)
        is_network = any("/" in t for t in targets)
        if skip_discovery and is_network:
            warnings.append(
                "Warning: -Pn with network range can be slow (scans all IPs regardless of host status)"
            )

        # === BUILD NMAP COMMAND ===
        # TCP Connect scan (-sT) doesn't require root
        # -n: no DNS resolution (prevents DNS leak)
        # --open: only show open ports
        cmd = ["nmap", "-sT", "-n", "--open", f"-{timing}"]

        if skip_discovery:
            cmd.append("-Pn")

        if use_top_ports:
            cmd.extend(["--top-ports", "100"])
        else:
            cmd.extend(["-p", ports])

        cmd.extend(targets)

        # === EXECUTE ===
        effective_timeout = timeout if timeout else self.default_timeout
        target_info = f"{len(targets)} targets" if len(targets) > 1 else targets[0]
        port_info = (
            "--top-ports 100" if use_top_ports else f"{count_ports(ports)} ports"
        )

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
            )

            # Build output with warnings first
            output_parts = []
            if warnings:
                output_parts.extend(warnings)
                output_parts.append("")  # Empty line after warnings

            output_parts.append(f"[Port Scan: {target_info}]")
            output_parts.append(f"[Ports: {port_info}] [Timing: {timing}]")
            output_parts.append("")

            if result.returncode == 0:
                output_parts.append(result.stdout)
            else:
                output_parts.append(f"Error: {result.stderr}")

            return "\n".join(output_parts)

        except subprocess.TimeoutExpired:
            # Include warnings even on timeout
            output_parts = []
            if warnings:
                output_parts.extend(warnings)
                output_parts.append("")
            output_parts.append(
                f"Error: Scan timeout (>{effective_timeout}s). Try fewer targets/ports or faster timing."
            )
            return "\n".join(output_parts)
        except Exception as e:
            output_parts = []
            if warnings:
                output_parts.extend(warnings)
                output_parts.append("")
            output_parts.append(f"Error: {e}")
            return "\n".join(output_parts)


if __name__ == "__main__":
    import sys

    tool = PortScannerTool()
    if len(sys.argv) < 2:
        print("Usage: python -m tools.network.port_scanner <target> [ports]")
        sys.exit(1)
    print(
        tool.execute(
            target=sys.argv[1],
            ports=sys.argv[2] if len(sys.argv) > 2 else None,
        )
    )
