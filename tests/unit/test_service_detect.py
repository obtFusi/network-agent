"""Tests for tools/network/service_detect.py"""

from unittest.mock import patch, MagicMock
import pytest
from tools.network.service_detect import ServiceDetectTool


@pytest.fixture
def mock_nmap_available():
    """Mock nmap availability check."""
    with patch("tools.network.service_detect.require_nmap") as mock:
        mock.return_value = (True, "")
        yield mock


class TestServiceDetectTool:
    def setup_method(self):
        self.tool = ServiceDetectTool()

    def test_name(self):
        assert self.tool.name == "service_detect"

    def test_description_mentions_service(self):
        assert "service" in self.tool.description.lower()

    def test_parameters_has_target(self):
        assert "target" in self.tool.parameters["properties"]
        assert "target" in self.tool.parameters["required"]

    def test_parameters_has_ports(self):
        assert "ports" in self.tool.parameters["properties"]

    def test_parameters_has_intensity(self):
        assert "intensity" in self.tool.parameters["properties"]

    def test_parameters_has_skip_discovery(self):
        assert "skip_discovery" in self.tool.parameters["properties"]

    def test_empty_target_rejected(self, mock_nmap_available):
        result = self.tool.execute("")
        assert "Validation error" in result

    def test_public_ip_rejected(self, mock_nmap_available):
        result = self.tool.execute("8.8.8.8")
        assert "Validation error" in result
        assert "public" in result.lower() or "Public" in result

    def test_ipv6_rejected(self, mock_nmap_available):
        result = self.tool.execute("::1")
        assert "Validation error" in result
        assert "IPv6" in result

    def test_intensity_too_low_rejected(self, mock_nmap_available):
        result = self.tool.execute("127.0.0.1", intensity=0)
        assert "Validation error" in result
        assert "1-9" in result

    def test_intensity_too_high_rejected(self, mock_nmap_available):
        result = self.tool.execute("127.0.0.1", intensity=10)
        assert "Validation error" in result
        assert "1-9" in result

    def test_intensity_valid_range(self, mock_nmap_available):
        """Valid intensity values should work."""
        with patch("tools.network.service_detect.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            for i in [1, 5, 9]:
                result = self.tool.execute("127.0.0.1", intensity=i)
                assert "Validation error" not in result

    @patch("tools.network.service_detect.subprocess.run")
    def test_uses_version_detection(self, mock_run, mock_nmap_available):
        """Should use -sV flag for version detection."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        self.tool.execute("127.0.0.1")
        cmd = mock_run.call_args[0][0]
        assert "-sV" in cmd

    @patch("tools.network.service_detect.subprocess.run")
    def test_uses_version_intensity(self, mock_run, mock_nmap_available):
        """Should use --version-intensity flag."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        self.tool.execute("127.0.0.1", intensity=7)
        cmd = mock_run.call_args[0][0]
        assert "--version-intensity=7" in cmd

    @patch("tools.network.service_detect.subprocess.run")
    def test_default_top_20_ports(self, mock_run, mock_nmap_available):
        """Without ports param, should use --top-ports 20."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        self.tool.execute("127.0.0.1")
        cmd = mock_run.call_args[0][0]
        assert "--top-ports" in cmd
        idx = cmd.index("--top-ports")
        assert cmd[idx + 1] == "20"

    @patch("tools.network.service_detect.subprocess.run")
    def test_skip_discovery_flag(self, mock_run, mock_nmap_available):
        """skip_discovery should add -Pn flag."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        self.tool.execute("127.0.0.1", skip_discovery=True)
        cmd = mock_run.call_args[0][0]
        assert "-Pn" in cmd

    @patch("tools.network.service_detect.subprocess.run")
    def test_warning_pn_with_network(self, mock_run, mock_nmap_available):
        """Warning when using -Pn with network range."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = self.tool.execute("127.0.0.0/30", skip_discovery=True)
        assert "Warning" in result

    @patch("tools.network.service_detect.subprocess.run")
    def test_successful_scan(self, mock_run, mock_nmap_available):
        """Successful scan should return results."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="PORT   STATE SERVICE VERSION\n22/tcp open  ssh     OpenSSH 8.9\n",
            stderr="",
        )
        result = self.tool.execute("127.0.0.1")
        assert "Service Detection" in result
        assert "OpenSSH" in result or "SERVICE" in result

    def test_network_too_large_rejected(self, mock_nmap_available):
        """Networks larger than /24 should be rejected."""
        result = self.tool.execute("192.168.0.0/16")
        assert "Validation error" in result


class TestServiceDetectTypeGuards:
    """Type guards for LLM input validation."""

    def setup_method(self):
        self.tool = ServiceDetectTool()

    def test_target_not_string_rejected(self):
        result = self.tool.execute(target=123)
        assert "Validation error" in result
        assert "target must be string" in result

    def test_ports_not_string_rejected(self):
        result = self.tool.execute(target="127.0.0.1", ports=80)
        assert "Validation error" in result
        assert "ports must be string" in result

    def test_intensity_not_int_rejected(self):
        result = self.tool.execute(target="127.0.0.1", intensity="5")
        assert "Validation error" in result
        assert "intensity must be integer" in result

    def test_intensity_bool_rejected(self):
        """Bool is int subclass, but should be rejected."""
        result = self.tool.execute(target="127.0.0.1", intensity=True)
        assert "Validation error" in result

    def test_skip_discovery_not_bool_rejected(self):
        result = self.tool.execute(target="127.0.0.1", skip_discovery="yes")
        assert "Validation error" in result

    def test_timeout_not_int_rejected(self):
        result = self.tool.execute(target="127.0.0.1", timeout="300")
        assert "Validation error" in result

    def test_timeout_bool_rejected(self):
        result = self.tool.execute(target="127.0.0.1", timeout=True)
        assert "Validation error" in result

    def test_timeout_zero_rejected(self):
        result = self.tool.execute(target="127.0.0.1", timeout=0)
        assert "Validation error" in result
        assert ">= 1" in result
