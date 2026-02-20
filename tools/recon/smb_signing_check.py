"""SMB Signing Check Tool.

Checks whether SMB signing is required on a target host.
Hosts without required SMB signing are vulnerable to
SMB relay attacks (NTLM relay).

Authorization: passive (only reads SMB negotiation response).
"""

import logging
from tools.base import BaseTool
from tools.validation import resolve_and_validate

logger = logging.getLogger(__name__)

try:
    from impacket.smbconnection import SMBConnection

    HAS_IMPACKET = True
except ImportError:
    HAS_IMPACKET = False


class SMBSigningCheckTool(BaseTool):
    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return "smb_signing_check"

    @property
    def description(self) -> str:
        return (
            "Checks if SMB signing is required on a target host. "
            "Hosts without required SMB signing are vulnerable to "
            "SMB relay attacks (NTLM authentication relay)."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Target host IP or hostname",
                },
                "port": {
                    "type": "integer",
                    "description": "SMB port (default: 445)",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Connection timeout in seconds (default: 10)",
                },
            },
            "required": ["target"],
        }

    @property
    def authorization_level(self) -> str:
        return "passive"

    @property
    def category(self) -> str:
        return "recon"

    def execute(self, target: str, port: int = 445, timeout: int = 10) -> str:
        # Type guards
        if not isinstance(target, str):
            return (
                f"Validation error: target must be string, got {type(target).__name__}"
            )
        if not isinstance(port, (int, float)):
            return f"Validation error: port must be integer, got {type(port).__name__}"
        if not isinstance(timeout, (int, float)):
            return f"Validation error: timeout must be integer, got {type(timeout).__name__}"
        port = int(port)
        timeout = int(timeout)

        if port < 1 or port > 65535:
            return "Validation error: port must be between 1 and 65535"
        if timeout < 1 or timeout > 60:
            return "Validation error: timeout must be between 1 and 60 seconds"

        # Dependency check
        if not HAS_IMPACKET:
            return "Error: impacket not installed. Install with: pip install impacket"

        # Target validation
        valid, error, ips = resolve_and_validate(target, allow_public=False)
        if not valid:
            return error

        target_ip = ips[0]

        try:
            # Connect and check SMB signing
            smb = SMBConnection(target_ip, target_ip, sess_port=port, timeout=timeout)

            signing_required = smb.isSigningRequired()
            smb_dialect = smb.getDialect()

            # Map dialect number to human-readable version
            dialect_map = {
                0x0202: "SMB 2.0.2",
                0x0210: "SMB 2.1",
                0x0300: "SMB 3.0",
                0x0302: "SMB 3.0.2",
                0x0311: "SMB 3.1.1",
            }
            dialect_str = dialect_map.get(smb_dialect, f"Unknown (0x{smb_dialect:04x})")

            try:
                server_name = smb.getServerName()
                server_domain = smb.getServerDomain()
                server_os = smb.getServerOS()
            except Exception:
                server_name = "N/A"
                server_domain = "N/A"
                server_os = "N/A"

            try:
                smb.close()
            except Exception:
                pass

            # Build output
            lines = [
                f"[SMB Signing Check: {target_ip}:{port}]",
                "",
                f"SMB Dialect: {dialect_str}",
                f"Server Name: {server_name}",
                f"Server Domain: {server_domain}",
                f"Server OS: {server_os}",
                "",
            ]

            if signing_required:
                lines.append("SMB Signing: REQUIRED")
                lines.append("Status: SECURE - SMB relay attacks are not possible")
                self.report_finding(
                    severity="info",
                    title="SMB signing required",
                    host=target_ip,
                    port=port,
                    description=f"SMB signing is required on {target_ip}:{port} ({dialect_str}). SMB relay attacks are not possible.",
                )
            else:
                lines.append("SMB Signing: NOT REQUIRED")
                lines.append(
                    "Status: VULNERABLE - Host is susceptible to SMB relay attacks"
                )
                lines.append("")
                lines.append(
                    "Remediation: Enable 'Microsoft network server: Digitally sign communications (always)' via Group Policy"
                )
                self.report_finding(
                    severity="high",
                    title="SMB signing not required",
                    host=target_ip,
                    port=port,
                    description=(
                        f"SMB signing is not required on {target_ip}:{port} ({dialect_str}). "
                        "This host is vulnerable to SMB relay attacks where an attacker "
                        "can forward captured NTLM authentication to this target."
                    ),
                    remediation=(
                        "Enable 'Microsoft network server: Digitally sign communications (always)' "
                        "in Group Policy under Computer Configuration > Policies > Windows Settings > "
                        "Security Settings > Local Policies > Security Options"
                    ),
                )

            return "\n".join(lines)

        except ConnectionRefusedError:
            return f"Error: Connection refused to {target_ip}:{port} - SMB service not available"
        except TimeoutError:
            return f"Error: Connection timeout to {target_ip}:{port} after {timeout}s"
        except OSError as e:
            return f"Error: Network error connecting to {target_ip}:{port}: {e}"
        except Exception as e:
            return f"Error: SMB check failed for {target_ip}:{port}: {e}"
