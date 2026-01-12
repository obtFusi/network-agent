"""
Tests for tools/validation.py

Tests input validation and sanitization functions.
Uses RFC 5737 TEST-NET addresses (192.0.2.0/24) for examples.
"""

import socket
from unittest.mock import patch
from tools.validation import (
    validate_network,
    validate_port_list,
    sanitize_hostname,
    resolve_and_validate,
    require_nmap,
)


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
        assert "Injection" in error or "Invalid" in error

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
        assert "too" in error.lower() or "large" in error.lower()

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
        # v5.4: MAX_PORTS is 1000, so 1-1000 is at the limit
        valid, error, normalized = validate_port_list("1-1000")
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
        assert "Empty" in error

    def test_port_limit(self):
        """v5.1: Too many ports rejected."""
        valid, error, _ = validate_port_list("1-2000")  # 2000 ports
        assert not valid
        assert "Too many ports" in error

    def test_whitespace_normalized(self):
        """v5.1: Whitespace removed."""
        valid, _, normalized = validate_port_list("22, 80, 443")
        assert valid
        assert normalized == "22,80,443"

    def test_error_prefix_consistent(self):
        """v5.1: Consistent error prefix."""
        valid, error, _ = validate_port_list("")
        assert error.startswith("Validation error:")


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


class TestResolveAndValidate:
    """Tests for resolve_and_validate() function."""

    # v5.4: Whitespace injection prevention
    def test_rejects_whitespace_in_target(self):
        """v5.4: Whitespace blocks injection like '192.168.1.1  --foo'."""
        valid, error, _ = resolve_and_validate("192.168.1.1  --foo")
        assert not valid
        assert "whitespace" in error.lower()

    def test_rejects_tab_in_target(self):
        """v5.4: Tab character blocked."""
        valid, error, _ = resolve_and_validate("host\tname")
        assert not valid
        assert "whitespace" in error.lower()

    def test_rejects_hostname_with_space(self):
        """v5.4: 'host name' is invalid."""
        valid, error, _ = resolve_and_validate("host name")
        assert not valid
        assert "whitespace" in error.lower()

    def test_rejects_public_ip(self):
        """v5.1: Public IP rejected."""
        valid, error, _ = resolve_and_validate("8.8.8.8")
        assert not valid
        assert "Public IP not allowed" in error

    def test_rejects_ipv6(self):
        """v5.1: IPv6 explicitly blocked."""
        valid, error, _ = resolve_and_validate("::1")
        assert not valid
        assert "IPv6 not supported" in error

    def test_rejects_ipv6_cidr(self):
        """v5.1: IPv6 CIDR blocked."""
        valid, error, _ = resolve_and_validate("fe80::/10")
        assert not valid
        assert "IPv6 not supported" in error

    @patch("tools.validation.socket.getaddrinfo")
    def test_rejects_public_hostname(self, mock_getaddrinfo):
        """v5.1: Mock getaddrinfo (not gethostbyname_ex)."""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("142.250.185.78", 0))  # Google IP
        ]
        valid, error, _ = resolve_and_validate("google.com")
        assert not valid
        assert "resolves to public IP" in error

    @patch("tools.validation.socket.getaddrinfo")
    def test_hostname_max_hosts_exceeded(self, mock_getaddrinfo):
        """v5.1: Hostname resolving to too many IPs."""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", (f"192.168.1.{i}", 0)) for i in range(300)
        ]
        valid, error, _ = resolve_and_validate("many-ips.local", max_hosts=256)
        assert not valid
        assert "too many IPs" in error

    @patch("tools.validation.socket.getaddrinfo")
    def test_hostname_multi_ip_all_returned(self, mock_getaddrinfo):
        """v5.1: All IPs returned, not just first."""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("192.168.1.10", 0)),
            (2, 1, 6, "", ("192.168.1.11", 0)),
            (2, 1, 6, "", ("192.168.1.10", 0)),  # Duplicate
        ]
        valid, _, targets = resolve_and_validate("multi.local")
        assert valid
        assert len(targets) == 2  # Deduplicated
        assert "192.168.1.10" in targets
        assert "192.168.1.11" in targets

    def test_exclude_ip_in_network(self):
        """RFC1918 IP excluded by network."""
        valid, error, _ = resolve_and_validate(
            "192.168.1.5", allow_public=False, exclude_list=["192.168.1.0/24"]
        )
        assert not valid
        assert "excluded" in error.lower()

    def test_exclude_network_overlap(self):
        """Network overlapping with exclude list rejected."""
        valid, error, _ = resolve_and_validate(
            "192.168.1.0/24", allow_public=False, exclude_list=["192.168.0.0/16"]
        )
        assert not valid
        assert "overlap" in error.lower()

    def test_cidr_size_limit(self):
        """CIDR exceeding max_hosts rejected."""
        valid, error, _ = resolve_and_validate(
            "10.0.0.0/8",  # 16M hosts
            max_hosts=256,
        )
        assert not valid
        assert "too large" in error.lower()

    def test_private_ip_allowed(self):
        """RFC1918 IP allowed."""
        valid, _, targets = resolve_and_validate("192.168.1.1")
        assert valid
        assert targets == ["192.168.1.1"]

    def test_loopback_allowed(self):
        """Loopback address allowed."""
        valid, _, targets = resolve_and_validate("127.0.0.1")
        assert valid

    # v5.2: Link-Local and CGNAT blocking
    def test_rejects_link_local(self):
        """v5.2: Link-Local address blocked."""
        valid, error, _ = resolve_and_validate("169.254.1.1")
        assert not valid
        assert "Link-Local" in error

    def test_rejects_cgnat(self):
        """v5.2: CGNAT address blocked."""
        valid, error, _ = resolve_and_validate("100.64.0.1")
        assert not valid
        assert "CGNAT" in error

    @patch("tools.validation.socket.getaddrinfo")
    def test_rejects_hostname_resolving_to_link_local(self, mock_getaddrinfo):
        """v5.2: Hostname resolving to Link-Local blocked."""
        mock_getaddrinfo.return_value = [(2, 1, 6, "", ("169.254.1.1", 0))]
        valid, error, _ = resolve_and_validate("link-local.example")
        assert not valid
        assert "blocked" in error.lower()

    def test_error_prefix_consistent(self):
        """v5.1: All errors start with 'Validation error:'."""
        valid, error, _ = resolve_and_validate("")
        assert not valid
        assert error.startswith("Validation error:")

    # v5.3: Trailing dot normalized
    def test_trailing_dot_normalized(self):
        """v5.3: Trailing dot in FQDN normalized."""
        valid, _, targets = resolve_and_validate("192.168.1.1.")
        assert valid
        assert targets == ["192.168.1.1"]  # Without trailing dot

    # v5.3: AAAA-only hostname detection
    @patch("tools.validation.socket.getaddrinfo")
    def test_rejects_ipv6_only_hostname(self, mock_getaddrinfo):
        """v5.3: Hostname with only AAAA records rejected."""

        def side_effect(target, port, family):
            if family == socket.AF_INET:
                raise socket.gaierror("no A records")
            elif family == socket.AF_INET6:
                return [(10, 1, 6, "", ("2001:db8::1", 0, 0, 0))]
            return []

        mock_getaddrinfo.side_effect = side_effect

        valid, error, _ = resolve_and_validate("ipv6only.example")
        assert not valid
        assert "IPv6" in error
        assert "AAAA" in error or "only IPv6" in error

    # v5.3: CIDR blocking for Link-Local
    def test_rejects_link_local_cidr(self):
        """v5.3: Link-Local CIDR blocked."""
        valid, error, _ = resolve_and_validate("169.254.0.0/24")
        assert not valid
        assert "Link-Local" in error

    # v5.3: CIDR blocking for CGNAT
    def test_rejects_cgnat_cidr(self):
        """v5.3: CGNAT CIDR blocked."""
        valid, error, _ = resolve_and_validate("100.64.0.0/24")
        assert not valid
        assert "CGNAT" in error

    # v5.7: Type guard tests
    def test_non_string_target_rejected(self):
        """v5.7: Non-string target rejected."""
        valid, error, _ = resolve_and_validate(["192.168.1.1"])
        assert not valid
        assert "must be string" in error


class TestRequireNmap:
    """v5.4: Centralized nmap check."""

    @patch("tools.validation.shutil.which")
    def test_nmap_not_found(self, mock_which):
        """nmap not installed returns error."""
        mock_which.return_value = None
        ok, error = require_nmap()
        assert not ok
        assert "nmap not found" in error

    @patch("tools.validation.shutil.which")
    def test_nmap_found(self, mock_which):
        """nmap installed returns success."""
        mock_which.return_value = "/usr/bin/nmap"
        ok, error = require_nmap()
        assert ok
        assert error == ""


class TestPingSweepNmapOrder:
    """v5.4: nmap-Check must come BEFORE _has_raw_socket_access."""

    # v5.7: Patch must be in the module where it's used!
    @patch("tools.network.ping_sweep.require_nmap")
    def test_nmap_check_before_has_raw_socket_access(self, mock_require_nmap):
        """v5.4: If nmap not found, _has_raw_socket_access should NOT be called."""
        mock_require_nmap.return_value = (
            False,
            "Error: nmap not found. Please install nmap.",
        )
        from tools.network.ping_sweep import PingSweepTool

        tool = PingSweepTool()

        # Mock _has_raw_socket_access to track if it's called
        with patch.object(tool, "_has_raw_socket_access") as mock_has_raw:
            result = tool.execute("192.168.1.0/24", method="auto")
            # Should return nmap error, NOT call _has_raw_socket_access
            assert "nmap not found" in result
            mock_has_raw.assert_not_called()


class TestPingSweepTypeGuards:
    """v5.8: Tool input type guards."""

    def test_network_not_string_rejected(self):
        """v5.8: Non-string network rejected."""
        from tools.network.ping_sweep import PingSweepTool

        tool = PingSweepTool()
        result = tool.execute(network=["192.168.1.0/24"])
        assert "Validation error" in result
        assert "must be string" in result

    def test_method_not_string_rejected(self):
        """v5.8: Non-string method rejected."""
        from tools.network.ping_sweep import PingSweepTool

        tool = PingSweepTool()
        result = tool.execute(network="192.168.1.1", method=123)
        assert "Validation error" in result
        assert "must be string" in result


class TestPingSweepConfigIntegration:
    """Tests for ping_sweep using config."""

    def test_config_error_returns_validation_error(self, tmp_path):
        """Config error returned as validation error."""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("scan: 'not-a-dict'\n")
        with patch.dict("os.environ", {"NETWORK_AGENT_CONFIG": str(config_file)}):
            from tools.config import reset_scan_config
            from tools.network.ping_sweep import PingSweepTool

            reset_scan_config()
            tool = PingSweepTool()
            result = tool.execute("192.168.1.1")
            assert "Validation error" in result
            assert "mapping" in result
