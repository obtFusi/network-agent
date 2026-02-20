"""
Tests for tools/recon/smb_signing_check.py

Uses mocking to avoid actual SMB connections in CI.
Uses RFC 5737 TEST-NET addresses (192.0.2.0/24) for examples.
"""

import pytest
from unittest.mock import patch, MagicMock
from tools.recon.smb_signing_check import SMBSigningCheckTool


class TestSMBSigningCheckTool:
    """Tests for SMBSigningCheckTool class."""

    @pytest.fixture
    def tool(self):
        return SMBSigningCheckTool()

    def test_tool_name(self, tool):
        assert tool.name == "smb_signing_check"

    def test_tool_description(self, tool):
        assert "SMB" in tool.description
        assert "signing" in tool.description.lower()

    def test_tool_parameters_schema(self, tool):
        params = tool.parameters
        assert params["type"] == "object"
        assert "target" in params["properties"]
        assert "port" in params["properties"]
        assert "timeout" in params["properties"]
        assert params["required"] == ["target"]

    def test_authorization_level_passive(self, tool):
        assert tool.authorization_level == "passive"

    def test_category_recon(self, tool):
        assert tool.category == "recon"

    def test_target_fields_default(self, tool):
        """Uses default target_fields (["target"])."""
        assert tool.target_fields == ["target"]

    # --- Type guard tests ---

    def test_target_type_guard(self, tool):
        result = tool.execute(target=123)
        assert "Validation error" in result
        assert "target" in result

    def test_port_type_guard(self, tool):
        result = tool.execute(target="192.0.2.1", port="abc")
        assert "Validation error" in result
        assert "port" in result

    def test_timeout_type_guard(self, tool):
        result = tool.execute(target="192.0.2.1", timeout="abc")
        assert "Validation error" in result
        assert "timeout" in result

    def test_port_range_low(self, tool):
        result = tool.execute(target="192.0.2.1", port=0)
        assert "Validation error" in result

    def test_port_range_high(self, tool):
        result = tool.execute(target="192.0.2.1", port=70000)
        assert "Validation error" in result

    def test_timeout_range_low(self, tool):
        result = tool.execute(target="192.0.2.1", timeout=0)
        assert "Validation error" in result

    def test_timeout_range_high(self, tool):
        result = tool.execute(target="192.0.2.1", timeout=999)
        assert "Validation error" in result

    # --- Target validation ---

    @patch("tools.recon.smb_signing_check.resolve_and_validate")
    def test_validates_target(self, mock_validate, tool):
        """Uses resolve_and_validate for target validation."""
        mock_validate.return_value = (False, "Validation error: public IP blocked", [])

        result = tool.execute(target="8.8.8.8")
        assert "Validation error" in result or "public" in result.lower()
        mock_validate.assert_called_once()

    # --- SMB check results ---

    @patch("tools.recon.smb_signing_check.resolve_and_validate")
    @patch("tools.recon.smb_signing_check.SMBConnection")
    def test_signing_required(self, mock_smb_class, mock_validate, tool):
        """Reports info when signing is required."""
        mock_validate.return_value = (True, None, ["192.0.2.1"])

        mock_smb = MagicMock()
        mock_smb.isSigningRequired.return_value = True
        mock_smb.getDialect.return_value = 0x0311
        mock_smb.getServerName.return_value = "DC01"
        mock_smb.getServerDomain.return_value = "CORP"
        mock_smb.getServerOS.return_value = "Windows Server 2022"
        mock_smb_class.return_value = mock_smb

        result = tool.execute(target="192.0.2.1")
        assert "REQUIRED" in result
        assert "SECURE" in result
        assert "SMB 3.1.1" in result
        assert "DC01" in result

    @patch("tools.recon.smb_signing_check.resolve_and_validate")
    @patch("tools.recon.smb_signing_check.SMBConnection")
    def test_signing_not_required(self, mock_smb_class, mock_validate, tool):
        """Reports high severity when signing is not required."""
        mock_validate.return_value = (True, None, ["192.0.2.1"])

        mock_smb = MagicMock()
        mock_smb.isSigningRequired.return_value = False
        mock_smb.getDialect.return_value = 0x0210
        mock_smb.getServerName.return_value = "WS01"
        mock_smb.getServerDomain.return_value = "WORKGROUP"
        mock_smb.getServerOS.return_value = "Windows 10"
        mock_smb_class.return_value = mock_smb

        result = tool.execute(target="192.0.2.1")
        assert "NOT REQUIRED" in result
        assert "VULNERABLE" in result
        assert "relay" in result.lower()

    @patch("tools.recon.smb_signing_check.resolve_and_validate")
    @patch("tools.recon.smb_signing_check.SMBConnection")
    def test_unknown_dialect(self, mock_smb_class, mock_validate, tool):
        """Handles unknown SMB dialect gracefully."""
        mock_validate.return_value = (True, None, ["192.0.2.1"])

        mock_smb = MagicMock()
        mock_smb.isSigningRequired.return_value = True
        mock_smb.getDialect.return_value = 0x9999
        mock_smb.getServerName.return_value = "SRV"
        mock_smb.getServerDomain.return_value = ""
        mock_smb.getServerOS.return_value = ""
        mock_smb_class.return_value = mock_smb

        result = tool.execute(target="192.0.2.1")
        assert "Unknown" in result

    # --- Error handling ---

    @patch("tools.recon.smb_signing_check.resolve_and_validate")
    @patch("tools.recon.smb_signing_check.SMBConnection")
    def test_connection_refused(self, mock_smb_class, mock_validate, tool):
        """Handles ConnectionRefusedError."""
        mock_validate.return_value = (True, None, ["192.0.2.1"])
        mock_smb_class.side_effect = ConnectionRefusedError()

        result = tool.execute(target="192.0.2.1")
        assert "Error" in result
        assert "refused" in result.lower()

    @patch("tools.recon.smb_signing_check.resolve_and_validate")
    @patch("tools.recon.smb_signing_check.SMBConnection")
    def test_timeout_error(self, mock_smb_class, mock_validate, tool):
        """Handles TimeoutError."""
        mock_validate.return_value = (True, None, ["192.0.2.1"])
        mock_smb_class.side_effect = TimeoutError()

        result = tool.execute(target="192.0.2.1")
        assert "Error" in result
        assert "timeout" in result.lower()

    @patch("tools.recon.smb_signing_check.resolve_and_validate")
    @patch("tools.recon.smb_signing_check.SMBConnection")
    def test_os_error(self, mock_smb_class, mock_validate, tool):
        """Handles OSError."""
        mock_validate.return_value = (True, None, ["192.0.2.1"])
        mock_smb_class.side_effect = OSError("Network unreachable")

        result = tool.execute(target="192.0.2.1")
        assert "Error" in result

    # --- report_finding integration ---

    @patch("tools.recon.smb_signing_check.resolve_and_validate")
    @patch("tools.recon.smb_signing_check.SMBConnection")
    def test_reports_finding_signing_not_required(
        self, mock_smb_class, mock_validate, tool
    ):
        """Calls report_finding when signing is not required."""
        mock_validate.return_value = (True, None, ["192.0.2.1"])

        mock_smb = MagicMock()
        mock_smb.isSigningRequired.return_value = False
        mock_smb.getDialect.return_value = 0x0300
        mock_smb.getServerName.return_value = "WS01"
        mock_smb.getServerDomain.return_value = "WORKGROUP"
        mock_smb.getServerOS.return_value = ""
        mock_smb_class.return_value = mock_smb

        with patch.object(tool, "report_finding") as mock_report:
            tool.execute(target="192.0.2.1")
            mock_report.assert_called_once()
            call_kwargs = mock_report.call_args[1]
            assert call_kwargs["severity"] == "high"
            assert "not required" in call_kwargs["title"].lower()

    # --- BaseTool integration ---

    def test_to_openai_format(self, tool):
        fmt = tool.to_openai_format()
        assert fmt["type"] == "function"
        assert fmt["function"]["name"] == "smb_signing_check"
