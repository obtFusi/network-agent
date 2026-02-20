import subprocess
from tools.base import BaseTool
from tools.validation import resolve_and_validate, require_nmap
from tools.config import get_scan_config


class PingSweepTool(BaseTool):
    # Standard ports for TCP-Connect Scan (when ICMP not available)
    COMMON_PORTS = "22,80,443,8080,3389,5900"

    def __init__(self):
        super().__init__()
        # v5.3: Lazy config - does NOT crash here
        self._config = get_scan_config()

    @property
    def name(self) -> str:
        return "ping_sweep"

    @property
    def description(self) -> str:
        return "Scans a network for active hosts. Uses ICMP Ping (Linux) or TCP-Connect (macOS/Windows Docker). Supports IP, CIDR, or hostname."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "network": {
                    "type": "string",
                    "description": "Target: IP address, CIDR notation (e.g., 192.168.1.0/24), or hostname",
                },
                "method": {
                    "type": "string",
                    "enum": ["auto", "icmp", "tcp"],
                    "description": "Scan method: auto (auto-detect), icmp (Ping), tcp (Port-Scan)",
                },
            },
            "required": ["network"],
        }

    @property
    def max_hosts(self) -> int:
        """v5.3: Use discovery limit (65536 = /16), not portscan limit!"""
        return self._config.max_hosts_discovery

    @property
    def exclude_list(self) -> list:
        return self._config.exclude_ips

    @property
    def timeout(self) -> int:
        """v5.3: Config-SSOT - actually use the timeout!"""
        return self._config.timeout

    def _has_raw_socket_access(self) -> bool:
        """Checks if raw sockets are available (for ICMP Ping)"""
        # Quick test: Try a ping on localhost
        try:
            result = subprocess.run(
                ["nmap", "-sn", "-n", "127.0.0.1"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            # If "Host is up" found, ICMP works
            return "Host is up" in result.stdout
        except Exception:
            return False

    def execute(self, network: str, method: str = "auto") -> str:
        """Execute network scan"""
        # v5.8: Tool-Input Type-Guards (LLM can send wrong types!)
        if not isinstance(network, str):
            return f"Validation error: network must be string, got {type(network).__name__}"
        if not isinstance(method, str):
            return (
                f"Validation error: method must be string, got {type(method).__name__}"
            )

        # v5.3: Check for config errors (Fail-Closed at execute time, not init)
        if config_error := self._config.get_error():
            return f"Validation error: {config_error}"

        # v5.4: nmap-Check BEFORE method selection! _has_raw_socket_access calls nmap.
        nmap_ok, nmap_error = require_nmap()
        if not nmap_ok:
            return nmap_error

        # === VALIDATION (Guardrails) ===
        valid, error, targets = resolve_and_validate(
            network,
            allow_public=False,
            max_hosts=self.max_hosts,
            exclude_list=self.exclude_list,
        )
        if not valid:
            return error  # Already has "Validation error:" prefix

        # v5.2: Order-preserving dedup (not sorted - preserves resolution order)
        targets = list(dict.fromkeys(targets))

        try:
            # Determine method - nmap already verified above
            if method == "auto":
                use_tcp = not self._has_raw_socket_access()
            elif method == "tcp":
                use_tcp = True
            else:  # icmp
                use_tcp = False

            # v5.3: Consistent output header for all tools
            target_info = f"{len(targets)} targets" if len(targets) > 1 else targets[0]

            if use_tcp:
                # TCP-Connect Scan (works everywhere)
                cmd = ["nmap", "-sT", "-n", "-p", self.COMMON_PORTS, "--open"]
                cmd.extend(targets)  # v5.1: All targets
                scan_type = "TCP-Connect"
            else:
                # ICMP Ping Sweep (needs raw sockets)
                cmd = ["nmap", "-sn", "-n"]
                cmd.extend(targets)  # v5.1: All targets
                scan_type = "ICMP Ping"

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,  # v5.3: Use config timeout
            )

            if result.returncode == 0:
                output = f"[Ping Sweep: {target_info}]\n[Scan Method: {scan_type}]\n\n{result.stdout}"
                return output
            else:
                return f"Error: {result.stderr}"

        except subprocess.TimeoutExpired:
            return f"Error: Scan timeout (>{self.timeout}s). Try a smaller subnet."
        except Exception as e:
            return f"Error: {str(e)}"
