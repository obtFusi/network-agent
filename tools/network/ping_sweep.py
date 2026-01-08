import subprocess
from tools.base import BaseTool


class PingSweepTool(BaseTool):
    @property
    def name(self) -> str:
        return "ping_sweep"

    @property
    def description(self) -> str:
        return "Scannt ein Netzwerk nach aktiven Hosts mittels nmap Ping Sweep"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "network": {
                    "type": "string",
                    "description": "Netzwerk in CIDR-Notation, z.B. 192.168.1.0/24"
                }
            },
            "required": ["network"]
        }

    def execute(self, network: str) -> str:
        """Führt nmap Ping Sweep aus"""
        try:
            result = subprocess.run(
                ["nmap", "-sn", network],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return result.stdout
            else:
                return f"Error: {result.stderr}"

        except subprocess.TimeoutExpired:
            return "Error: Scan timeout (>30s)"
        except Exception as e:
            return f"Error: {str(e)}"
