"""
Tests for tools/network/ping_sweep.py

Uses mocking to avoid actual nmap execution in CI.
Uses RFC 5737 TEST-NET addresses (192.0.2.0/24) for examples.
"""

import pytest
from unittest.mock import patch, MagicMock
from tools.network.ping_sweep import PingSweepTool


class TestPingSweepTool:
    """Tests for PingSweepTool class."""

    @pytest.fixture
    def tool(self):
        """Create a PingSweepTool instance."""
        return PingSweepTool()

    def test_tool_name(self, tool):
        """Tool has correct name."""
        assert tool.name == "ping_sweep"

    def test_tool_has_description(self, tool):
        """Tool has a description."""
        assert len(tool.description) > 0

    def test_tool_parameters_schema(self, tool):
        """Tool has correct parameter schema."""
        params = tool.parameters
        assert params["type"] == "object"
        assert "network" in params["properties"]
        assert "network" in params["required"]

    def test_execute_validates_input(self, tool):
        """Execute validates network input before scanning."""
        # Invalid input should return validation error
        result = tool.execute(network="-sV")
        assert "Validierungsfehler" in result or "Error" in result

    def test_execute_blocks_injection(self, tool):
        """Execute blocks injection attempts."""
        result = tool.execute(network="192.168.1.0/24; rm -rf /")
        assert "Validierungsfehler" in result

    @patch("tools.network.ping_sweep.subprocess.run")
    def test_execute_calls_nmap(self, mock_run, tool):
        """Execute calls nmap with correct parameters."""
        # Mock successful nmap response
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Host: 192.0.2.1 ()\tStatus: Up"
        mock_run.return_value = mock_result

        # Also mock _has_raw_socket_access to return True (ICMP mode)
        with patch.object(tool, "_has_raw_socket_access", return_value=True):
            result = tool.execute(network="192.0.2.0/28")

        # Verify nmap was called
        mock_run.assert_called()
        call_args = mock_run.call_args[0][0]
        assert "nmap" in call_args
        assert "192.0.2.0/28" in call_args

    @patch("tools.network.ping_sweep.subprocess.run")
    def test_execute_icmp_mode(self, mock_run, tool):
        """Execute uses ICMP ping sweep when raw sockets available."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Host is up"
        mock_run.return_value = mock_result

        with patch.object(tool, "_has_raw_socket_access", return_value=True):
            tool.execute(network="192.0.2.0/28", method="icmp")

        call_args = mock_run.call_args[0][0]
        assert "-sn" in call_args  # ICMP ping sweep flag

    @patch("tools.network.ping_sweep.subprocess.run")
    def test_execute_tcp_mode(self, mock_run, tool):
        """Execute uses TCP connect scan when specified."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "PORT STATE"
        mock_run.return_value = mock_result

        tool.execute(network="192.0.2.0/28", method="tcp")

        call_args = mock_run.call_args[0][0]
        assert "-sT" in call_args  # TCP connect scan flag

    @patch("tools.network.ping_sweep.subprocess.run")
    def test_execute_returns_output(self, mock_run, tool):
        """Execute returns nmap output."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = (
            "Host: 192.0.2.1 ()\tStatus: Up\nHost: 192.0.2.2 ()\tStatus: Up"
        )
        mock_run.return_value = mock_result

        with patch.object(tool, "_has_raw_socket_access", return_value=True):
            result = tool.execute(network="192.0.2.0/28")

        assert "192.0.2.1" in result
        assert "192.0.2.2" in result

    @patch("tools.network.ping_sweep.subprocess.run")
    def test_execute_handles_timeout(self, mock_run, tool):
        """Execute handles nmap timeout gracefully."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="nmap", timeout=60)

        with patch.object(tool, "_has_raw_socket_access", return_value=True):
            result = tool.execute(network="192.0.2.0/28")

        assert "timeout" in result.lower()

    @patch("tools.network.ping_sweep.subprocess.run")
    def test_execute_handles_error(self, mock_run, tool):
        """Execute handles nmap errors gracefully."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "nmap: permission denied"
        mock_run.return_value = mock_result

        with patch.object(tool, "_has_raw_socket_access", return_value=True):
            result = tool.execute(network="192.0.2.0/28")

        assert "Error" in result

    def test_network_normalization(self, tool):
        """Network address gets normalized."""
        # This test verifies that 192.168.1.100/24 gets normalized to 192.168.1.0/24
        # by the validation layer before nmap is called
        with patch("tools.network.ping_sweep.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Host is up"
            mock_run.return_value = mock_result

            with patch.object(tool, "_has_raw_socket_access", return_value=True):
                tool.execute(network="192.0.2.100/28")

            call_args = mock_run.call_args[0][0]
            # Should be normalized to network address
            assert "192.0.2.96/28" in call_args


class TestHasRawSocketAccess:
    """Tests for _has_raw_socket_access() method."""

    @pytest.fixture
    def tool(self):
        return PingSweepTool()

    @patch("tools.network.ping_sweep.subprocess.run")
    def test_returns_true_when_ping_works(self, mock_run, tool):
        """Returns True when ICMP ping works."""
        mock_result = MagicMock()
        mock_result.stdout = "Host is up"
        mock_run.return_value = mock_result

        assert tool._has_raw_socket_access() is True

    @patch("tools.network.ping_sweep.subprocess.run")
    def test_returns_false_when_ping_fails(self, mock_run, tool):
        """Returns False when ICMP ping doesn't work."""
        mock_result = MagicMock()
        mock_result.stdout = "Note: Host seems down"
        mock_run.return_value = mock_result

        assert tool._has_raw_socket_access() is False

    @patch("tools.network.ping_sweep.subprocess.run")
    def test_returns_false_on_exception(self, mock_run, tool):
        """Returns False when nmap throws exception."""
        mock_run.side_effect = Exception("nmap not found")

        assert tool._has_raw_socket_access() is False
