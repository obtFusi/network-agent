"""LLMNR/NBT-NS Detector Tool.

Passive detection of LLMNR (UDP 5355) and NBT-NS (UDP 137) traffic
on the local network. Hosts responding to these protocols are
vulnerable to poisoning attacks (e.g., Responder).

Authorization: passive (read-only packet capture).
"""

import logging
import threading
from tools.base import BaseTool

logger = logging.getLogger(__name__)

try:
    from scapy.all import sniff, UDP, IP, conf

    HAS_SCAPY = True
except ImportError:
    HAS_SCAPY = False

# LLMNR destination: 224.0.0.252:5355
LLMNR_PORT = 5355
LLMNR_MCAST = "224.0.0.252"

# NBT-NS destination: broadcast on UDP 137
NBTNS_PORT = 137


class LLMNRDetectorTool(BaseTool):
    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return "llmnr_detector"

    @property
    def description(self) -> str:
        return (
            "Passively detects LLMNR (UDP 5355) and NBT-NS (UDP 137) traffic "
            "on the network. Hosts using these protocols are vulnerable to "
            "name resolution poisoning attacks."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "interface": {
                    "type": "string",
                    "description": "Network interface to listen on (default: auto-detect)",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Capture duration in seconds (default: 30)",
                },
            },
            "required": [],
        }

    @property
    def authorization_level(self) -> str:
        return "passive"

    @property
    def category(self) -> str:
        return "recon"

    @property
    def target_fields(self) -> list:
        return ["interface"]

    def execute(self, interface: str = "auto", timeout: int = 30) -> str:
        # Type guards
        if not isinstance(interface, str):
            return f"Validation error: interface must be string, got {type(interface).__name__}"
        if not isinstance(timeout, (int, float)):
            return f"Validation error: timeout must be integer, got {type(timeout).__name__}"
        timeout = int(timeout)
        if timeout < 1 or timeout > 300:
            return "Validation error: timeout must be between 1 and 300 seconds"

        # Dependency check
        if not HAS_SCAPY:
            return "Error: scapy not installed. Install with: pip install scapy"

        # Auto-detect interface
        if interface == "auto":
            interface = conf.iface
            if not interface:
                return "Error: Could not auto-detect network interface"

        # Collected results
        llmnr_hosts = {}  # ip -> count
        nbtns_hosts = {}  # ip -> count
        lock = threading.Lock()

        def packet_handler(pkt):
            if not pkt.haslayer(IP) or not pkt.haslayer(UDP):
                return

            src_ip = pkt[IP].src
            dst_port = pkt[UDP].dport

            with lock:
                if dst_port == LLMNR_PORT:
                    llmnr_hosts[src_ip] = llmnr_hosts.get(src_ip, 0) + 1
                elif dst_port == NBTNS_PORT:
                    nbtns_hosts[src_ip] = nbtns_hosts.get(src_ip, 0) + 1

        try:
            # Capture filter: UDP port 5355 (LLMNR) or UDP port 137 (NBT-NS)
            bpf_filter = f"udp port {LLMNR_PORT} or udp port {NBTNS_PORT}"

            sniff(
                iface=interface,
                filter=bpf_filter,
                prn=packet_handler,
                timeout=timeout,
                store=False,
            )
        except PermissionError:
            return (
                "Error: Insufficient permissions for packet capture. "
                "Run with root/CAP_NET_RAW: docker run --cap-add NET_RAW ..."
            )
        except OSError as e:
            return f"Error: Network interface error: {e}"
        except Exception as e:
            return f"Error: Capture failed: {e}"

        # Build output
        lines = [
            "[LLMNR/NBT-NS Detector]",
            f"[Interface: {interface}]",
            f"[Duration: {timeout}s]",
            "",
        ]

        total_hosts = set(llmnr_hosts.keys()) | set(nbtns_hosts.keys())

        if not total_hosts:
            lines.append("No LLMNR or NBT-NS traffic detected during capture period.")
            return "\n".join(lines)

        # LLMNR results
        if llmnr_hosts:
            lines.append(f"LLMNR Traffic (UDP {LLMNR_PORT}):")
            for ip, count in sorted(llmnr_hosts.items()):
                lines.append(f"  {ip} - {count} packet(s)")
                self.report_finding(
                    severity="medium",
                    title="LLMNR responder detected",
                    host=ip,
                    port=LLMNR_PORT,
                    protocol="udp",
                    description=(
                        f"Host {ip} is sending LLMNR queries. "
                        "LLMNR is vulnerable to poisoning attacks (e.g., Responder)."
                    ),
                    remediation="Disable LLMNR via Group Policy: Computer Configuration > Administrative Templates > Network > DNS Client > Turn off Multicast Name Resolution = Enabled",
                )
            lines.append("")

        # NBT-NS results
        if nbtns_hosts:
            lines.append(f"NBT-NS Traffic (UDP {NBTNS_PORT}):")
            for ip, count in sorted(nbtns_hosts.items()):
                lines.append(f"  {ip} - {count} packet(s)")
                self.report_finding(
                    severity="medium",
                    title="NBT-NS responder detected",
                    host=ip,
                    port=NBTNS_PORT,
                    protocol="udp",
                    description=(
                        f"Host {ip} is sending NBT-NS queries. "
                        "NBT-NS is vulnerable to poisoning attacks."
                    ),
                    remediation="Disable NetBIOS over TCP/IP in network adapter settings or via DHCP option 001",
                )
            lines.append("")

        lines.append(
            f"Total: {len(total_hosts)} unique host(s) with broadcast name resolution"
        )
        lines.append(
            "Risk: These hosts are vulnerable to LLMNR/NBT-NS poisoning (NTLM hash capture)"
        )

        return "\n".join(lines)
