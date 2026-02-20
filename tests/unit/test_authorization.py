"""Tests for 3-tier authorization system."""

import time

from tools.authorization import AuthorizationConfig, AuthorizationLevel
from tools.base import ToolResult


class TestAuthorizationLevel:
    def test_passive_numeric(self):
        assert AuthorizationLevel.PASSIVE.numeric == 0

    def test_active_numeric(self):
        assert AuthorizationLevel.ACTIVE.numeric == 1

    def test_destructive_numeric(self):
        assert AuthorizationLevel.DESTRUCTIVE.numeric == 2

    def test_passive_allows_passive(self):
        assert AuthorizationLevel.PASSIVE.allows(AuthorizationLevel.PASSIVE)

    def test_passive_denies_active(self):
        assert not AuthorizationLevel.PASSIVE.allows(AuthorizationLevel.ACTIVE)

    def test_passive_denies_destructive(self):
        assert not AuthorizationLevel.PASSIVE.allows(AuthorizationLevel.DESTRUCTIVE)

    def test_active_allows_passive(self):
        assert AuthorizationLevel.ACTIVE.allows(AuthorizationLevel.PASSIVE)

    def test_active_allows_active(self):
        assert AuthorizationLevel.ACTIVE.allows(AuthorizationLevel.ACTIVE)

    def test_active_denies_destructive(self):
        assert not AuthorizationLevel.ACTIVE.allows(AuthorizationLevel.DESTRUCTIVE)

    def test_destructive_allows_all(self):
        assert AuthorizationLevel.DESTRUCTIVE.allows(AuthorizationLevel.PASSIVE)
        assert AuthorizationLevel.DESTRUCTIVE.allows(AuthorizationLevel.ACTIVE)
        assert AuthorizationLevel.DESTRUCTIVE.allows(AuthorizationLevel.DESTRUCTIVE)


class TestAuthorizationConfig:
    """Test all 12 authorization combinations from the test matrix."""

    # Matrix row 1: passive config + passive required = ALLOWED
    def test_passive_config_passive_tool(self):
        config = AuthorizationConfig("passive")
        allowed, msg = config.check("ping_sweep", "passive")
        assert allowed is True
        assert msg == ""

    # Matrix row 2: passive config + active required = DENIED
    def test_passive_config_active_tool(self):
        config = AuthorizationConfig("passive")
        allowed, msg = config.check("llmnr_poisoner", "active")
        assert allowed is False
        assert "--i-have-written-authorization" in msg

    # Matrix row 3: passive config + destructive required = DENIED
    def test_passive_config_destructive_tool(self):
        config = AuthorizationConfig("passive")
        allowed, msg = config.check("pass_the_hash", "destructive")
        assert allowed is False

    # Matrix row 4: active config + passive required = ALLOWED
    def test_active_config_passive_tool(self):
        config = AuthorizationConfig("active")
        allowed, msg = config.check("ping_sweep", "passive")
        assert allowed is True

    # Matrix row 5: active config + active required = ALLOWED
    def test_active_config_active_tool(self):
        config = AuthorizationConfig("active")
        allowed, msg = config.check("llmnr_poisoner", "active")
        assert allowed is True

    # Matrix row 6: active config + destructive required = DENIED
    def test_active_config_destructive_tool(self):
        config = AuthorizationConfig("active")
        allowed, msg = config.check("pass_the_hash", "destructive")
        assert allowed is False

    # Matrix row 7: destructive config + passive required = ALLOWED
    def test_destructive_config_passive_tool(self):
        config = AuthorizationConfig("destructive")
        allowed, msg = config.check("ping_sweep", "passive")
        assert allowed is True

    # Matrix row 8: destructive config + active required = ALLOWED
    def test_destructive_config_active_tool(self):
        config = AuthorizationConfig("destructive")
        allowed, msg = config.check("llmnr_poisoner", "active")
        assert allowed is True

    # Matrix row 9: destructive config + destructive (unconfirmed) = ALLOWED
    # (check() allows it, confirmation is a separate step in agent core)
    def test_destructive_config_destructive_tool_allowed(self):
        config = AuthorizationConfig("destructive")
        allowed, msg = config.check("pass_the_hash", "destructive")
        assert allowed is True

    # Matrix row 10: destructive confirmed = no re-confirmation needed
    def test_destructive_confirmed_no_reconfirmation(self):
        config = AuthorizationConfig("destructive")
        config.confirm_destructive("pass_the_hash", "10.0.0.1")
        assert not config.requires_confirmation("pass_the_hash", "10.0.0.1")

    # Matrix row 11: destructive TTL expired = needs re-confirmation
    def test_destructive_ttl_expired(self):
        config = AuthorizationConfig("destructive")
        config.confirm_destructive("pass_the_hash", "10.0.0.1")
        # Manually set timestamp to past
        key = ("pass_the_hash", "10.0.0.1")
        config._destructive_confirmed_at[key] = time.time() - 7200  # 2 hours ago
        assert config.requires_confirmation("pass_the_hash", "10.0.0.1")

    # Matrix row 12: confirmed for target A, calling target B = DENIED
    def test_destructive_different_target_needs_confirmation(self):
        config = AuthorizationConfig("destructive")
        config.confirm_destructive("pass_the_hash", "10.0.0.1")
        # Target A confirmed, but target B needs its own confirmation
        assert not config.requires_confirmation("pass_the_hash", "10.0.0.1")
        assert config.requires_confirmation("pass_the_hash", "10.0.0.2")

    def test_invalid_level_defaults_to_passive(self):
        config = AuthorizationConfig("invalid_level")
        assert config.level == AuthorizationLevel.PASSIVE

    def test_unknown_required_level_denied(self):
        config = AuthorizationConfig("active")
        allowed, msg = config.check("tool", "unknown_level")
        assert allowed is False
        assert "Unknown authorization level" in msg

    def test_unconfirmed_requires_confirmation(self):
        config = AuthorizationConfig("destructive")
        assert config.requires_confirmation("any_tool", "any_target")


class TestBaseToolDefaults:
    """Test BaseTool default property values."""

    def test_default_authorization_level(self):
        from tools.recon.ping_sweep import PingSweepTool

        tool = PingSweepTool()
        assert tool.authorization_level == "passive"

    def test_default_category(self):
        from tools.recon.ping_sweep import PingSweepTool

        tool = PingSweepTool()
        assert tool.category == "recon"

    def test_default_target_fields(self):
        from tools.recon.ping_sweep import PingSweepTool

        tool = PingSweepTool()
        assert tool.target_fields == ["target"]

    def test_findings_store_none_by_default(self):
        from tools.recon.dns_lookup import DNSLookupTool

        tool = DNSLookupTool()
        assert tool._findings_store is None

    def test_report_finding_noop_without_store(self):
        from tools.recon.dns_lookup import DNSLookupTool

        tool = DNSLookupTool()
        # Should not raise
        tool.report_finding(severity="high", title="Test finding", host="10.0.0.1")


class TestToolResult:
    def test_basic_creation(self):
        result = ToolResult(status="completed", message="scan done")
        assert result.status == "completed"
        assert result.message == "scan done"
        assert result.error_type is None

    def test_with_error_type(self):
        result = ToolResult(
            status="failed", message="nmap not found", error_type="dependency"
        )
        assert result.status == "failed"
        assert result.error_type == "dependency"

    def test_denied_status(self):
        result = ToolResult(status="denied", message="auth required", error_type="auth")
        assert result.status == "denied"
