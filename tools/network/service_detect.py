"""Service Detection Tool - Identify services and versions on open ports."""

import subprocess
from typing import List
from tools.base import BaseTool
from tools.validation import (
    resolve_and_validate,
    require_nmap,
    validate_port_list,
)
from tools.config import get_scan_config


class ServiceDetectTool(BaseTool):
    # Default timeout is longer for service detection (slow probes)
    DEFAULT_TIMEOUT = 300

    def __init__(self):
        super().__init__()
        self._config = get_scan_config()

    @property
    def name(self) -> str:
        return "service_detect"

    @property
    def description(self) -> str:
        return (
            "Detects services and versions running on open ports. "
            "Slower than port_scanner but provides service names and versions. "
            "Supports single IPs, hostnames, or networks (max /24). Private networks only."
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
                    "description": "Port list (22,80,443) or range. Default: top 20 ports",
                },
                "intensity": {
                    "type": "integer",
                    "description": "Probe intensity 1-9 (higher = more probes, slower). Default: 5",
                },
                "skip_discovery": {
                    "type": "boolean",
                    "description": "Skip host discovery (-Pn). Use for hosts that block ping.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds. Default: 300 (service detection is slow)",
                },
            },
            "required": ["target"],
        }

    @property
    def max_hosts(self) -> int:
        return self._config.max_hosts_portscan

    @property
    def exclude_list(self) -> List[str]:
        return self._config.exclude_ips

    def execute(
        self,
        target: str,
        ports: str = None,
        intensity: int = 5,
        skip_discovery: bool = False,
        timeout: int = None,
    ) -> str:
        """Execute service detection scan."""
        warnings: List[str] = []

        # === TYPE GUARDS ===
        if not isinstance(target, str):
            return (
                f"Validation error: target must be string, got {type(target).__name__}"
            )
        if ports is not None and not isinstance(ports, str):
            return f"Validation error: ports must be string, got {type(ports).__name__}"
        # intensity: int check (exclude bool!)
        if type(intensity) is not int:
            return f"Validation error: intensity must be integer, got {type(intensity).__name__}"
        if not 1 <= intensity <= 9:
            return f"Validation error: intensity must be 1-9, got {intensity}"
        if not isinstance(skip_discovery, bool):
            return f"Validation error: skip_discovery must be boolean, got {type(skip_discovery).__name__}"
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
            use_top_ports = True
        else:
            valid, error, normalized = validate_port_list(ports)
            if not valid:
                return error
            ports = normalized

        # === WARNINGS ===
        is_network = any("/" in t for t in targets)
        if skip_discovery and is_network:
            warnings.append(
                "Warning: -Pn with network range can be very slow for service detection"
            )

        # === BUILD NMAP COMMAND ===
        # -sV: Version detection
        # -sT: TCP Connect (no root needed)
        # -n: No DNS resolution
        # --open: Only show open ports
        cmd = ["nmap", "-sT", "-sV", "-n", "--open"]
        cmd.append(f"--version-intensity={intensity}")

        if skip_discovery:
            cmd.append("-Pn")

        if use_top_ports:
            cmd.extend(["--top-ports", "20"])
        else:
            cmd.extend(["-p", ports])

        cmd.extend(targets)

        # === EXECUTE ===
        effective_timeout = timeout if timeout else self.DEFAULT_TIMEOUT
        target_info = f"{len(targets)} targets" if len(targets) > 1 else targets[0]
        port_info = "--top-ports 20" if use_top_ports else f"ports {ports}"

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
            )

            output_parts = []
            if warnings:
                output_parts.extend(warnings)
                output_parts.append("")

            output_parts.append(f"[Service Detection: {target_info}]")
            output_parts.append(f"[{port_info}] [Intensity: {intensity}]")
            output_parts.append("")

            if result.returncode == 0:
                output_parts.append(result.stdout)
            else:
                output_parts.append(f"Error: {result.stderr}")

            return "\n".join(output_parts)

        except subprocess.TimeoutExpired:
            output_parts = []
            if warnings:
                output_parts.extend(warnings)
                output_parts.append("")
            output_parts.append(
                f"Error: Scan timeout (>{effective_timeout}s). Service detection is slow - try fewer targets or lower intensity."
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

    tool = ServiceDetectTool()
    if len(sys.argv) < 2:
        print("Usage: python -m tools.network.service_detect <target> [ports]")
        sys.exit(1)
    print(
        tool.execute(
            target=sys.argv[1],
            ports=sys.argv[2] if len(sys.argv) > 2 else None,
        )
    )
