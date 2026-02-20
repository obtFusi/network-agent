"""
Tests for tools/harvest/kerberoast.py

Uses mocking to avoid actual Kerberos/LDAP operations in CI.
Uses RFC 5737 TEST-NET addresses (192.0.2.0/24) for examples.
"""

import pytest
from unittest.mock import patch
from tools.harvest.kerberoast import KerberoastTool


class TestKerberoastTool:
    """Tests for KerberoastTool class."""

    @pytest.fixture
    def tool(self):
        return KerberoastTool()

    def test_tool_name(self, tool):
        assert tool.name == "kerberoast"

    def test_tool_description(self, tool):
        assert "Kerberoast" in tool.description
        assert "SPN" in tool.description

    def test_tool_parameters_schema(self, tool):
        params = tool.parameters
        assert params["type"] == "object"
        assert "target" in params["properties"]
        assert "domain" in params["properties"]
        assert "username" in params["properties"]
        assert "password" in params["properties"]
        assert set(params["required"]) == {"target", "domain", "username", "password"}

    def test_authorization_level_active(self, tool):
        """Kerberoasting requires active authorization."""
        assert tool.authorization_level == "active"

    def test_category_harvest(self, tool):
        assert tool.category == "harvest"

    def test_target_fields(self, tool):
        """Scope enforcement checks both target and domain."""
        assert tool.target_fields == ["target", "domain"]

    # --- Type guard tests ---

    def test_target_type_guard(self, tool):
        result = tool.execute(
            target=123, domain="corp.local", username="user", password="pass"
        )
        assert "Validation error" in result
        assert "target" in result

    def test_domain_type_guard(self, tool):
        result = tool.execute(
            target="192.0.2.1", domain=123, username="user", password="pass"
        )
        assert "Validation error" in result
        assert "domain" in result

    def test_username_type_guard(self, tool):
        result = tool.execute(
            target="192.0.2.1", domain="corp.local", username=123, password="pass"
        )
        assert "Validation error" in result
        assert "username" in result

    def test_password_type_guard(self, tool):
        result = tool.execute(
            target="192.0.2.1", domain="corp.local", username="user", password=123
        )
        assert "Validation error" in result
        assert "password" in result

    def test_empty_domain_validation(self, tool):
        result = tool.execute(
            target="192.0.2.1", domain="", username="user", password="pass"
        )
        assert "Validation error" in result
        assert "domain" in result

    def test_empty_username_validation(self, tool):
        result = tool.execute(
            target="192.0.2.1", domain="corp.local", username="", password="pass"
        )
        assert "Validation error" in result
        assert "username" in result

    def test_empty_password_validation(self, tool):
        result = tool.execute(
            target="192.0.2.1", domain="corp.local", username="user", password="  "
        )
        assert "Validation error" in result
        assert "password" in result

    # --- Target validation ---

    @patch("tools.harvest.kerberoast.resolve_and_validate")
    def test_validates_target(self, mock_validate, tool):
        """Uses resolve_and_validate for target IP validation."""
        mock_validate.return_value = (False, "Validation error: public IP blocked", [])

        result = tool.execute(
            target="8.8.8.8", domain="corp.local", username="user", password="pass"
        )
        assert "Validation error" in result or "public" in result.lower()

    # --- Error handling ---

    @patch("tools.harvest.kerberoast.resolve_and_validate")
    def test_auth_failed_error(self, mock_validate, tool):
        """Handles authentication failure."""
        mock_validate.return_value = (True, None, ["192.0.2.1"])

        with patch.object(tool, "_enumerate_spns") as mock_enum:
            mock_enum.side_effect = Exception("KDC_ERR_PREAUTH_FAILED")
            result = tool.execute(
                target="192.0.2.1",
                domain="corp.local",
                username="baduser",
                password="badpass",
            )

        assert "Error" in result
        assert (
            "invalid credentials" in result.lower() or "Authentication failed" in result
        )

    @patch("tools.harvest.kerberoast.resolve_and_validate")
    def test_user_not_found_error(self, mock_validate, tool):
        """Handles unknown user error."""
        mock_validate.return_value = (True, None, ["192.0.2.1"])

        with patch.object(tool, "_enumerate_spns") as mock_enum:
            mock_enum.side_effect = Exception("KDC_ERR_C_PRINCIPAL_UNKNOWN")
            result = tool.execute(
                target="192.0.2.1",
                domain="corp.local",
                username="nonexist",
                password="pass",
            )

        assert "Error" in result
        assert "not found" in result.lower()

    @patch("tools.harvest.kerberoast.resolve_and_validate")
    def test_connection_error(self, mock_validate, tool):
        """Handles connection failure."""
        mock_validate.return_value = (True, None, ["192.0.2.1"])

        with patch.object(tool, "_enumerate_spns") as mock_enum:
            mock_enum.side_effect = Exception("Connection refused")
            result = tool.execute(
                target="192.0.2.1",
                domain="corp.local",
                username="user",
                password="pass",
            )

        assert "Error" in result
        assert "connect" in result.lower()

    @patch("tools.harvest.kerberoast.resolve_and_validate")
    def test_generic_error(self, mock_validate, tool):
        """Handles unexpected errors."""
        mock_validate.return_value = (True, None, ["192.0.2.1"])

        with patch.object(tool, "_enumerate_spns") as mock_enum:
            mock_enum.side_effect = Exception("Something unexpected")
            result = tool.execute(
                target="192.0.2.1",
                domain="corp.local",
                username="user",
                password="pass",
            )

        assert "Error" in result
        assert "Kerberoasting failed" in result

    # --- Output format tests ---

    @patch("tools.harvest.kerberoast.resolve_and_validate")
    def test_no_spns_found(self, mock_validate, tool):
        """Returns clean message when no SPNs found."""
        mock_validate.return_value = (True, None, ["192.0.2.1"])

        with patch.object(tool, "_enumerate_spns") as mock_enum:
            mock_enum.return_value = (
                "[Kerberoasting: 192.0.2.1]\n"
                "[Domain: corp.local]\n"
                "[Authenticated as: corp.local\\user]\n"
                "\n"
                "No Kerberoastable service accounts found."
            )
            result = tool.execute(
                target="192.0.2.1",
                domain="corp.local",
                username="user",
                password="pass",
            )

        assert "No Kerberoastable" in result

    @patch("tools.harvest.kerberoast.resolve_and_validate")
    def test_spns_found(self, mock_validate, tool):
        """Returns SPN details when accounts found."""
        mock_validate.return_value = (True, None, ["192.0.2.1"])

        with patch.object(tool, "_enumerate_spns") as mock_enum:
            mock_enum.return_value = (
                "[Kerberoasting: 192.0.2.1]\n"
                "[Domain: corp.local]\n"
                "[Authenticated as: corp.local\\user]\n"
                "\n"
                "Found 1 Kerberoastable account(s):\n"
                "\n"
                "  Account: svc_sql [ADMIN]\n"
                "  Password Last Set: 2024-01-01\n"
                "    SPN: MSSQLSvc/sql01.corp.local:1433\n"
                "    TGS Hash: [extracted - 1234 bytes]\n"
                "\n"
                "Total: 1 Kerberoastable account(s) found"
            )
            result = tool.execute(
                target="192.0.2.1",
                domain="corp.local",
                username="user",
                password="pass",
            )

        assert "Kerberoastable" in result
        assert "svc_sql" in result

    # --- BaseTool integration ---

    def test_to_openai_format(self, tool):
        fmt = tool.to_openai_format()
        assert fmt["type"] == "function"
        assert fmt["function"]["name"] == "kerberoast"

    def test_report_finding_noop_without_store(self, tool):
        """report_finding is a no-op when no store is set."""
        tool.report_finding(
            severity="high",
            title="Kerberoastable SPN found: svc_test",
            host="192.0.2.1",
            port=88,
            protocol="tcp",
        )
