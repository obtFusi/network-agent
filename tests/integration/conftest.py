"""Integration test configuration for the Pentest Lab.

SSOT for all lab network constants. All integration tests
reference these values instead of hardcoding IPs.

Usage:
    docker compose -f docker-compose.pentest-lab.yml up -d
    docker compose -f docker-compose.pentest-lab.yml exec attacker \
        pytest tests/integration/ -v
"""

import socket

import pytest

# === NETWORK CONSTANTS (SSOT) ===
# These must match docker-compose.pentest-lab.yml
LAB_SUBNET = "172.30.0.0/24"
LAB_GATEWAY = "172.30.0.1"

ATTACKER_IP = "172.30.0.10"
SAMBA_IP = "172.30.0.20"
SNMP_IP = "172.30.0.30"
WEBSERVER_IP = "172.30.0.40"
FTP_IP = "172.30.0.50"
TELNET_IP = "172.30.0.60"
LDAP_IP = "172.30.0.70"

# === CREDENTIALS (Lab only - intentionally weak) ===
SAMBA_USER = "admin"
SAMBA_PASS = "password123"
LDAP_ADMIN_DN = "cn=admin,dc=lab,dc=local"
LDAP_ADMIN_PASS = "admin123"
LDAP_BASE_DN = "dc=lab,dc=local"
LDAP_DOMAIN = "lab.local"
FTP_USER = "ftpuser"
FTP_PASS = "ftp123"
SNMP_COMMUNITY = "public"

# === SERVICE PORTS ===
SMB_PORT = 445
SNMP_PORT = 161
HTTP_PORT = 80
FTP_PORT = 21
TELNET_PORT = 23
LDAP_PORT = 389


def _is_lab_reachable() -> bool:
    """Check if the pentest lab is running by probing the webserver."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((WEBSERVER_IP, HTTP_PORT))
        sock.close()
        return result == 0
    except (socket.error, OSError):
        return False


# Skip all integration tests if lab is not running
lab_available = pytest.mark.skipif(
    not _is_lab_reachable(),
    reason="Pentest lab not running (docker compose -f docker-compose.pentest-lab.yml up -d)",
)


@pytest.fixture
def lab_subnet():
    """Return the lab subnet CIDR."""
    return LAB_SUBNET


@pytest.fixture
def samba_target():
    """Return Samba connection details."""
    return {
        "ip": SAMBA_IP,
        "port": SMB_PORT,
        "user": SAMBA_USER,
        "password": SAMBA_PASS,
    }


@pytest.fixture
def ldap_target():
    """Return LDAP connection details."""
    return {
        "ip": LDAP_IP,
        "port": LDAP_PORT,
        "admin_dn": LDAP_ADMIN_DN,
        "admin_pass": LDAP_ADMIN_PASS,
        "base_dn": LDAP_BASE_DN,
        "domain": LDAP_DOMAIN,
    }


@pytest.fixture
def snmp_target():
    """Return SNMP connection details."""
    return {
        "ip": SNMP_IP,
        "port": SNMP_PORT,
        "community": SNMP_COMMUNITY,
    }


@pytest.fixture
def webserver_target():
    """Return webserver connection details."""
    return {
        "ip": WEBSERVER_IP,
        "port": HTTP_PORT,
    }


@pytest.fixture
def ftp_target():
    """Return FTP connection details."""
    return {
        "ip": FTP_IP,
        "port": FTP_PORT,
        "user": FTP_USER,
        "password": FTP_PASS,
    }
