"""
Tests for tools/validation.py

Tests input validation and sanitization functions.
Uses RFC 5737 TEST-NET addresses (192.0.2.0/24) for examples.
"""

import pytest
from tools.validation import validate_network, validate_port_list, sanitize_hostname


class TestValidateNetwork:
    """Tests for validate_network() function."""

    def test_valid_private_cidr(self):
        """Valid private network in CIDR notation."""
        valid, error, normalized = validate_network("192.168.1.0/24")
        assert valid is True
        assert error == ""
        assert normalized == "192.168.1.0/24"

    def test_valid_cidr_normalizes(self):
        """Non-network address gets normalized to network address."""
        valid, error, normalized = validate_network("192.168.1.100/24")
        assert valid is True
        assert normalized == "192.168.1.0/24"

    def test_valid_small_subnet(self):
        """Small subnet is valid."""
        valid, error, normalized = validate_network("10.0.0.0/30")
        assert valid is True
        assert normalized == "10.0.0.0/30"

    def test_valid_single_host(self):
        """Single host (/32) is valid."""
        valid, error, normalized = validate_network("192.168.1.1/32")
        assert valid is True
        assert normalized == "192.168.1.1/32"

    # Injection protection tests
    def test_injection_semicolon(self):
        """Semicolon injection attempt is blocked."""
        valid, error, _ = validate_network("192.168.1.0/24; rm -rf /")
        assert valid is False
        assert "Injection" in error or "Ungültige Zeichen" in error

    def test_injection_pipe(self):
        """Pipe injection attempt is blocked."""
        valid, error, _ = validate_network("192.168.1.0/24 | cat /etc/passwd")
        assert valid is False

    def test_injection_backtick(self):
        """Backtick injection attempt is blocked."""
        valid, error, _ = validate_network("`whoami`")
        assert valid is False

    def test_injection_dollar(self):
        """Dollar sign injection attempt is blocked."""
        valid, error, _ = validate_network("$(cat /etc/passwd)")
        assert valid is False

    def test_nmap_option_blocked(self):
        """nmap options (starting with -) are blocked."""
        valid, error, _ = validate_network("-sV")
        assert valid is False
        assert "'-'" in error or "nmap" in error.lower()

    def test_nmap_option_elaborate(self):
        """Elaborate nmap option injection is blocked."""
        valid, error, _ = validate_network("-sV -p 22,80 192.168.1.0/24")
        assert valid is False

    # Size limit tests
    def test_network_too_large(self):
        """Network exceeding max_hosts is rejected."""
        # /8 has 16M+ hosts
        valid, error, _ = validate_network("10.0.0.0/8", max_hosts=65536)
        assert valid is False
        assert "zu groß" in error.lower() or "too" in error.lower()

    def test_network_at_limit(self):
        """/16 network (65536 hosts) is at default limit."""
        valid, error, normalized = validate_network("10.0.0.0/16", max_hosts=65536)
        assert valid is True

    # Public/private tests
    def test_public_ip_allowed_by_default(self):
        """Public IPs are allowed when allow_public=True (default)."""
        valid, error, _ = validate_network("8.8.8.0/24", allow_public=True)
        assert valid is True

    def test_public_ip_blocked_when_disabled(self):
        """Public IPs are blocked when allow_public=False."""
        valid, error, _ = validate_network("8.8.8.0/24", allow_public=False)
        assert valid is False
        assert "privat" in error.lower() or "public" in error.lower()

    # Invalid input tests
    def test_empty_input(self):
        """Empty input is rejected."""
        valid, error, _ = validate_network("")
        assert valid is False

    def test_whitespace_only(self):
        """Whitespace-only input is rejected."""
        valid, error, _ = validate_network("   ")
        assert valid is False

    def test_invalid_cidr_format(self):
        """Invalid CIDR format is rejected."""
        valid, error, _ = validate_network("not-a-network")
        assert valid is False

    def test_multicast_blocked(self):
        """Multicast networks are blocked."""
        valid, error, _ = validate_network("224.0.0.0/24")
        assert valid is False
        assert "Multicast" in error


class TestValidatePortList:
    """Tests for validate_port_list() function."""

    def test_single_port(self):
        """Single port is valid."""
        valid, error, normalized = validate_port_list("80")
        assert valid is True
        assert normalized == "80"

    def test_multiple_ports(self):
        """Comma-separated ports are valid."""
        valid, error, normalized = validate_port_list("22,80,443")
        assert valid is True
        assert normalized == "22,80,443"

    def test_port_range(self):
        """Port range is valid."""
        valid, error, normalized = validate_port_list("1-1024")
        assert valid is True

    def test_mixed_ports_and_ranges(self):
        """Mix of ports and ranges is valid."""
        valid, error, _ = validate_port_list("22,80,100-200,443")
        assert valid is True

    def test_port_out_of_range_high(self):
        """Port > 65535 is rejected."""
        valid, error, _ = validate_port_list("70000")
        assert valid is False

    def test_port_zero(self):
        """Port 0 is rejected."""
        valid, error, _ = validate_port_list("0")
        assert valid is False

    def test_injection_in_ports(self):
        """Injection attempt in ports is blocked."""
        valid, error, _ = validate_port_list("22; rm -rf /")
        assert valid is False

    def test_empty_ports(self):
        """Empty port list is rejected."""
        valid, error, _ = validate_port_list("")
        assert valid is False


class TestSanitizeHostname:
    """Tests for sanitize_hostname() function."""

    def test_valid_hostname(self):
        """Valid hostname is accepted."""
        valid, error, sanitized = sanitize_hostname("example.com")
        assert valid is True
        assert sanitized == "example.com"

    def test_valid_ip(self):
        """Valid IP address is accepted."""
        valid, error, sanitized = sanitize_hostname("192.168.1.1")
        assert valid is True
        assert sanitized == "192.168.1.1"

    def test_hostname_lowercased(self):
        """Hostname is lowercased."""
        valid, error, sanitized = sanitize_hostname("Example.COM")
        assert valid is True
        assert sanitized == "example.com"

    def test_injection_blocked(self):
        """Injection in hostname is blocked."""
        valid, error, _ = sanitize_hostname("example.com; cat /etc/passwd")
        assert valid is False

    def test_empty_hostname(self):
        """Empty hostname is rejected."""
        valid, error, _ = sanitize_hostname("")
        assert valid is False
