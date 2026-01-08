import subprocess
import os
from tools.base import BaseTool
from tools.validation import validate_network


class PingSweepTool(BaseTool):
    # Standard-Ports für TCP-Connect Scan (wenn ICMP nicht verfügbar)
    COMMON_PORTS = "22,80,443,8080,3389,5900"

    # Konfigurierbare Limits
    MAX_HOSTS = 65536  # /16 Maximum
    ALLOW_PUBLIC = True  # Öffentliche IPs erlauben

    @property
    def name(self) -> str:
        return "ping_sweep"

    @property
    def description(self) -> str:
        return "Scannt ein Netzwerk nach aktiven Hosts. Nutzt ICMP Ping (Linux) oder TCP-Connect (macOS/Windows Docker)."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "network": {
                    "type": "string",
                    "description": "Netzwerk in CIDR-Notation, z.B. 192.168.1.0/24"
                },
                "method": {
                    "type": "string",
                    "enum": ["auto", "icmp", "tcp"],
                    "description": "Scan-Methode: auto (erkennt automatisch), icmp (Ping), tcp (Port-Scan)"
                }
            },
            "required": ["network"]
        }

    def _has_raw_socket_access(self) -> bool:
        """Prüft ob Raw Sockets verfügbar sind (für ICMP Ping)"""
        # Schneller Test: Versuche einen Ping auf localhost
        try:
            result = subprocess.run(
                ["nmap", "-sn", "-n", "127.0.0.1"],
                capture_output=True,
                text=True,
                timeout=5
            )
            # Wenn "Host is up" gefunden wird, funktioniert ICMP
            return "Host is up" in result.stdout
        except:
            return False

    def execute(self, network: str, method: str = "auto") -> str:
        """Führt Netzwerk-Scan aus"""
        # === VALIDIERUNG (Guardrails) ===
        valid, error, normalized_network = validate_network(
            network,
            max_hosts=self.MAX_HOSTS,
            allow_public=self.ALLOW_PUBLIC
        )
        if not valid:
            return f"Validierungsfehler: {error}"

        # Normalisiertes Netzwerk verwenden (z.B. 192.168.1.1/24 -> 192.168.1.0/24)
        network = normalized_network

        try:
            # Methode bestimmen
            if method == "auto":
                use_tcp = not self._has_raw_socket_access()
            elif method == "tcp":
                use_tcp = True
            else:  # icmp
                use_tcp = False

            if use_tcp:
                # TCP-Connect Scan (funktioniert überall)
                cmd = ["nmap", "-sT", "-p", self.COMMON_PORTS, "--open", network]
                scan_type = "TCP-Connect"
            else:
                # ICMP Ping Sweep (braucht Raw Sockets)
                cmd = ["nmap", "-sn", network]
                scan_type = "ICMP Ping"

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60  # TCP-Scan braucht länger
            )

            if result.returncode == 0:
                output = f"[Scan-Methode: {scan_type}]\n\n{result.stdout}"
                return output
            else:
                return f"Error: {result.stderr}"

        except subprocess.TimeoutExpired:
            return "Error: Scan timeout (>60s). Versuche ein kleineres Subnetz."
        except Exception as e:
            return f"Error: {str(e)}"
