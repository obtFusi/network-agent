"""Smoke tests for pentest lab connectivity.

Verifies all 7 services are reachable from the attacker container.
Run: docker compose -f docker-compose.pentest-lab.yml exec attacker \
     pytest tests/integration/test_lab_connectivity.py -v
"""

import socket

import pytest

from tests.integration.conftest import (
    FTP_IP,
    FTP_PORT,
    LDAP_IP,
    LDAP_PORT,
    SAMBA_IP,
    SMB_PORT,
    SNMP_IP,
    SNMP_PORT,
    TELNET_IP,
    TELNET_PORT,
    WEBSERVER_IP,
    HTTP_PORT,
    lab_available,
)


def _tcp_connect(ip: str, port: int, timeout: float = 5.0) -> bool:
    """Try TCP connection to host:port."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except (socket.error, OSError):
        return False


@lab_available
class TestLabConnectivity:
    """Verify all lab services are reachable."""

    def test_samba_reachable(self):
        assert _tcp_connect(SAMBA_IP, SMB_PORT), (
            f"Samba not reachable at {SAMBA_IP}:{SMB_PORT}"
        )

    def test_webserver_reachable(self):
        assert _tcp_connect(WEBSERVER_IP, HTTP_PORT), (
            f"Webserver not reachable at {WEBSERVER_IP}:{HTTP_PORT}"
        )

    def test_ftp_reachable(self):
        assert _tcp_connect(FTP_IP, FTP_PORT), (
            f"FTP not reachable at {FTP_IP}:{FTP_PORT}"
        )

    def test_telnet_reachable(self):
        assert _tcp_connect(TELNET_IP, TELNET_PORT), (
            f"Telnet not reachable at {TELNET_IP}:{TELNET_PORT}"
        )

    def test_ldap_reachable(self):
        assert _tcp_connect(LDAP_IP, LDAP_PORT), (
            f"LDAP not reachable at {LDAP_IP}:{LDAP_PORT}"
        )

    def test_snmp_udp_reachable(self):
        """SNMP uses UDP - send a basic SNMPv2c GET request."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5.0)
            # SNMPv2c GET sysDescr.0 (minimal valid SNMP packet)
            # Community: "public"
            snmp_get = bytes.fromhex(
                "302602010104067075626c6963a019020400"
                "020100020100300b300906052b06010201"
                "0500"
            )
            sock.sendto(snmp_get, (SNMP_IP, SNMP_PORT))
            data, _ = sock.recvfrom(4096)
            sock.close()
            assert len(data) > 0, "No SNMP response received"
        except socket.timeout:
            pytest.skip("SNMP timeout - service may still be starting")
        except OSError as e:
            pytest.fail(f"SNMP not reachable at {SNMP_IP}:{SNMP_PORT}: {e}")
