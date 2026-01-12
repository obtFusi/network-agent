"""Tests for tools/network/port_scanner.py"""

from unittest.mock import patch, MagicMock
import pytest
from tools.network.port_scanner import PortScannerTool


@pytest.fixture
def mock_nmap_available():
    """Mock nmap availability check."""
    with patch("tools.network.port_scanner.require_nmap") as mock:
        mock.return_value = (True, "")
        yield mock


class TestPortScannerTool:
    def setup_method(self):
        self.tool = PortScannerTool()

    def test_name(self):
        assert self.tool.name == "port_scanner"

    def test_description_mentions_ports(self):
        assert "port" in self.tool.description.lower()

    def test_parameters_has_target(self):
        assert "target" in self.tool.parameters["properties"]
        assert "target" in self.tool.parameters["required"]

    def test_parameters_has_ports(self):
        assert "ports" in self.tool.parameters["properties"]

    def test_parameters_has_timing(self):
        assert "timing" in self.tool.parameters["properties"]
        assert "enum" in self.tool.parameters["properties"]["timing"]

    def test_parameters_has_skip_discovery(self):
        assert "skip_discovery" in self.tool.parameters["properties"]

    def test_empty_target_rejected(self, mock_nmap_available):
        result = self.tool.execute("")
        assert "Validation error" in result

    def test_whitespace_only_target_rejected(self, mock_nmap_available):
        result = self.tool.execute("   ")
        assert "Validation error" in result

    def test_public_ip_rejected(self, mock_nmap_available):
        """Public IPs should be rejected."""
        result = self.tool.execute("8.8.8.8")
        assert "Validation error" in result
        assert "Public IP" in result or "public" in result.lower()

    def test_ipv6_rejected(self, mock_nmap_available):
        """IPv6 should be rejected."""
        result = self.tool.execute("::1")
        assert "Validation error" in result
        assert "IPv6" in result

    def test_invalid_timing_rejected(self, mock_nmap_available):
        """Invalid timing template should be rejected."""
        result = self.tool.execute("192.168.1.1", timing="T99")
        assert "Validation error" in result
        assert "timing" in result.lower()

    def test_timing_case_insensitive(self, mock_nmap_available):
        """Lowercase timing should work."""
        with patch("tools.network.port_scanner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = self.tool.execute("127.0.0.1", timing="t3")
            assert "Validation error" not in result

    def test_invalid_ports_rejected(self, mock_nmap_available):
        """Invalid port list should be rejected."""
        result = self.tool.execute("127.0.0.1", ports="abc")
        assert "Validation error" in result

    def test_too_many_ports_rejected(self, mock_nmap_available):
        """More than 1000 ports should be rejected."""
        result = self.tool.execute("127.0.0.1", ports="1-1001")
        assert "Validation error" in result
        assert "Too many ports" in result

    def test_port_range_valid(self, mock_nmap_available):
        """Valid port range should work."""
        with patch("tools.network.port_scanner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = self.tool.execute("127.0.0.1", ports="1-1000")
            assert "Validation error" not in result

    def test_port_list_valid(self, mock_nmap_available):
        """Valid port list should work."""
        with patch("tools.network.port_scanner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = self.tool.execute("127.0.0.1", ports="22,80,443")
            assert "Validation error" not in result

    @patch("tools.network.port_scanner.subprocess.run")
    def test_successful_scan(self, mock_run, mock_nmap_available):
        """Successful scan should return results."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="PORT   STATE SERVICE\n22/tcp open  ssh\n",
            stderr="",
        )
        result = self.tool.execute("127.0.0.1", ports="22")
        assert "Port Scan" in result
        assert "22/tcp" in result or "PORT" in result

    @patch("tools.network.port_scanner.subprocess.run")
    def test_uses_tcp_connect_scan(self, mock_run, mock_nmap_available):
        """Should use TCP Connect scan (-sT)."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        self.tool.execute("127.0.0.1", ports="22")
        cmd = mock_run.call_args[0][0]
        assert "-sT" in cmd

    @patch("tools.network.port_scanner.subprocess.run")
    def test_uses_no_dns_flag(self, mock_run, mock_nmap_available):
        """Should use -n flag to prevent DNS leak."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        self.tool.execute("127.0.0.1", ports="22")
        cmd = mock_run.call_args[0][0]
        assert "-n" in cmd

    @patch("tools.network.port_scanner.subprocess.run")
    def test_skip_discovery_flag(self, mock_run, mock_nmap_available):
        """skip_discovery should add -Pn flag."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        self.tool.execute("127.0.0.1", ports="22", skip_discovery=True)
        cmd = mock_run.call_args[0][0]
        assert "-Pn" in cmd

    @patch("tools.network.port_scanner.subprocess.run")
    def test_warning_pn_with_network(self, mock_run, mock_nmap_available):
        """Warning when using -Pn with network range."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = self.tool.execute("127.0.0.0/30", ports="22", skip_discovery=True)
        assert "Warning" in result
        assert "-Pn" in result or "slow" in result.lower()

    @patch("tools.network.port_scanner.subprocess.run")
    @patch("tools.network.port_scanner.get_scan_config")
    def test_default_top_ports(self, mock_get_config, mock_run, mock_nmap_available):
        """Without ports param and no config ports, should use --top-ports."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        # Create mock config with no tcp_ports
        mock_config = MagicMock()
        mock_config.get_error.return_value = None
        mock_config.tcp_ports = None
        mock_config.max_hosts_portscan = 256
        mock_config.exclude_ips = []
        mock_config.timeout = 120
        mock_get_config.return_value = mock_config
        # Create new tool instance with mocked config
        tool = PortScannerTool()
        tool.execute("127.0.0.1")
        cmd = mock_run.call_args[0][0]
        assert "--top-ports" in cmd

    def test_network_too_large_rejected(self, mock_nmap_available):
        """Networks larger than /24 should be rejected."""
        result = self.tool.execute("192.168.0.0/16")
        assert "Validation error" in result
        assert "too large" in result.lower() or "max" in result.lower()


class TestPortScannerTypeGuards:
    """Type guards for LLM input validation."""

    def setup_method(self):
        self.tool = PortScannerTool()

    def test_target_not_string_rejected(self):
        result = self.tool.execute(target=123)
        assert "Validation error" in result
        assert "target must be string" in result

    def test_ports_not_string_rejected(self):
        result = self.tool.execute(target="127.0.0.1", ports=123)
        assert "Validation error" in result
        assert "ports must be string" in result

    def test_timing_not_string_rejected(self):
        result = self.tool.execute(target="127.0.0.1", timing=3)
        assert "Validation error" in result
        assert "timing must be string" in result

    def test_skip_discovery_not_bool_rejected(self):
        result = self.tool.execute(target="127.0.0.1", skip_discovery="yes")
        assert "Validation error" in result
        assert "skip_discovery must be boolean" in result

    def test_timeout_not_int_rejected(self):
        result = self.tool.execute(target="127.0.0.1", timeout="60")
        assert "Validation error" in result
        assert "timeout must be integer" in result

    def test_timeout_bool_rejected(self):
        """Bool is int subclass, but should be rejected."""
        result = self.tool.execute(target="127.0.0.1", timeout=True)
        assert "Validation error" in result
        assert "timeout must be integer" in result

    def test_timeout_zero_rejected(self):
        result = self.tool.execute(target="127.0.0.1", timeout=0)
        assert "Validation error" in result
        assert ">= 1" in result

    def test_timeout_negative_rejected(self):
        result = self.tool.execute(target="127.0.0.1", timeout=-5)
        assert "Validation error" in result
