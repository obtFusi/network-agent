"""Tests for Agent Core Integration: authorization, scope, findings, tool-call limit."""

from unittest.mock import patch


from agent.core import NetworkAgent
from tools.authorization import AuthorizationConfig
from tools.base import BaseTool, ToolResult
from tools.findings_store import FindingsStore
from tools.scope import ScopeConfig


# --- Test Tool Fixtures ---


class PassiveTool(BaseTool):
    """Test tool with passive authorization."""

    def __init__(self):
        super().__init__()

    @property
    def name(self):
        return "passive_tool"

    @property
    def description(self):
        return "A passive test tool"

    @property
    def parameters(self):
        return {"type": "object", "properties": {"target": {"type": "string"}}}

    @property
    def authorization_level(self):
        return "passive"

    def execute(self, **kwargs):
        return "passive result"


class ActiveTool(BaseTool):
    """Test tool with active authorization."""

    def __init__(self):
        super().__init__()

    @property
    def name(self):
        return "active_tool"

    @property
    def description(self):
        return "An active test tool"

    @property
    def parameters(self):
        return {"type": "object", "properties": {"target": {"type": "string"}}}

    @property
    def authorization_level(self):
        return "active"

    def execute(self, **kwargs):
        return "active result"


class DestructiveTool(BaseTool):
    """Test tool with destructive authorization."""

    def __init__(self):
        super().__init__()

    @property
    def name(self):
        return "destructive_tool"

    @property
    def description(self):
        return "A destructive test tool"

    @property
    def parameters(self):
        return {"type": "object", "properties": {"target": {"type": "string"}}}

    @property
    def authorization_level(self):
        return "destructive"

    def execute(self, **kwargs):
        return "destructive result"


class ToolResultTool(BaseTool):
    """Test tool that returns ToolResult."""

    def __init__(self):
        super().__init__()

    @property
    def name(self):
        return "toolresult_tool"

    @property
    def description(self):
        return "A tool returning ToolResult"

    @property
    def parameters(self):
        return {"type": "object", "properties": {"target": {"type": "string"}}}

    def execute(self, **kwargs):
        return ToolResult(status="completed", message="structured result")


class ErrorTool(BaseTool):
    """Test tool that returns error string."""

    def __init__(self):
        super().__init__()

    @property
    def name(self):
        return "error_tool"

    @property
    def description(self):
        return "A tool that errors"

    @property
    def parameters(self):
        return {"type": "object", "properties": {"target": {"type": "string"}}}

    def execute(self, **kwargs):
        return "Error: something went wrong"


class ExceptionTool(BaseTool):
    """Test tool that raises an exception."""

    def __init__(self):
        super().__init__()

    @property
    def name(self):
        return "exception_tool"

    @property
    def description(self):
        return "A tool that raises"

    @property
    def parameters(self):
        return {"type": "object", "properties": {"target": {"type": "string"}}}

    def execute(self, **kwargs):
        raise RuntimeError("tool crashed")


# --- Helpers ---


def make_config(**overrides):
    """Create minimal agent config."""
    config = {
        "llm": {
            "provider": {
                "model": "test-model",
                "base_url": "http://localhost:1234/v1",
                "temperature": 0.7,
                "max_tokens": 1024,
            }
        },
        "agent": {"max_iterations": 5, "verbose": False},
    }
    for key, value in overrides.items():
        if "." in key:
            parts = key.split(".")
            d = config
            for p in parts[:-1]:
                d = d.setdefault(p, {})
            d[parts[-1]] = value
        else:
            config[key] = value
    return config


def make_agent(
    tools=None,
    auth_config=None,
    findings_store=None,
    scope_config=None,
    max_tool_calls=200,
):
    """Create a NetworkAgent with mocked LLM and custom tools."""
    config = make_config()
    config.setdefault("scan", {})["max_tool_calls"] = max_tool_calls

    with (
        patch("agent.core.LLMClient"),
        patch("agent.core.get_all_tools") as mock_tools,
    ):
        mock_tools.return_value = tools or [PassiveTool()]
        agent = NetworkAgent(
            config=config,
            system_prompt="Test prompt",
            auth_config=auth_config,
            findings_store=findings_store,
            scope_config=scope_config,
        )
    return agent


# --- Test Classes ---


class TestExecuteToolBasic:
    def test_passive_tool_no_auth(self):
        """Passive tool works without auth config."""
        agent = make_agent(tools=[PassiveTool()])
        result = agent._execute_tool("passive_tool", {"target": "10.0.0.1"})
        assert result == "passive result"

    def test_unknown_tool(self):
        """Unknown tool returns error."""
        agent = make_agent(tools=[PassiveTool()])
        result = agent._execute_tool("nonexistent_tool", {})
        assert "not found" in result.lower()

    def test_tool_result_returned_directly(self):
        """ToolResult message is returned as-is."""
        agent = make_agent(tools=[ToolResultTool()])
        result = agent._execute_tool("toolresult_tool", {"target": "10.0.0.1"})
        assert result == "structured result"

    def test_exception_in_tool(self):
        """Exceptions in tool are caught."""
        agent = make_agent(tools=[ExceptionTool()])
        result = agent._execute_tool("exception_tool", {"target": "10.0.0.1"})
        assert "error" in result.lower()
        assert "tool crashed" in result.lower()


class TestLegacyStringAdapter:
    def test_error_string_maps_to_failed(self):
        """Error: prefix maps to failed status."""
        agent = make_agent(tools=[ErrorTool()])
        result = agent._execute_tool("error_tool", {"target": "10.0.0.1"})
        assert "Error:" in result

    def test_validation_error_string(self):
        """Validation error: prefix maps to failed with validation type."""

        class ValidationErrorTool(BaseTool):
            def __init__(self):
                super().__init__()

            @property
            def name(self):
                return "val_tool"

            @property
            def description(self):
                return "validation test"

            @property
            def parameters(self):
                return {"type": "object", "properties": {}}

            def execute(self, **kwargs):
                return "Validation error: bad input"

        agent = make_agent(tools=[ValidationErrorTool()])
        result = agent._execute_tool("val_tool", {})
        assert "Validation error" in result


class TestAuthorizationEnforcement:
    def test_active_tool_denied_without_auth(self):
        """Active tool denied when auth level is passive."""
        auth = AuthorizationConfig(level="passive")
        agent = make_agent(tools=[ActiveTool()], auth_config=auth)
        result = agent._execute_tool("active_tool", {"target": "10.0.0.1"})
        assert "denied" in result.lower()
        assert "authorization" in result.lower()

    def test_active_tool_allowed_with_active_auth(self):
        """Active tool allowed when auth level is active."""
        auth = AuthorizationConfig(level="active")
        agent = make_agent(tools=[ActiveTool()], auth_config=auth)
        result = agent._execute_tool("active_tool", {"target": "10.0.0.1"})
        assert result == "active result"

    def test_passive_tool_always_allowed(self):
        """Passive tool works regardless of auth config."""
        auth = AuthorizationConfig(level="passive")
        agent = make_agent(tools=[PassiveTool()], auth_config=auth)
        result = agent._execute_tool("passive_tool", {"target": "10.0.0.1"})
        assert result == "passive result"

    def test_destructive_denied_with_active_auth(self):
        """Destructive tool denied even with active auth."""
        auth = AuthorizationConfig(level="active")
        agent = make_agent(tools=[DestructiveTool()], auth_config=auth)
        result = agent._execute_tool("destructive_tool", {"target": "10.0.0.1"})
        assert "denied" in result.lower()

    def test_destructive_denied_non_interactive(self):
        """Destructive tool denied in non-interactive mode (no TTY)."""
        auth = AuthorizationConfig(level="destructive")
        agent = make_agent(tools=[DestructiveTool()], auth_config=auth)

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            result = agent._execute_tool("destructive_tool", {"target": "10.0.0.1"})

        assert "denied" in result.lower()
        assert "non-interactive" in result.lower()

    def test_destructive_allowed_after_confirmation(self):
        """Destructive tool allowed after CLI confirmation."""
        auth = AuthorizationConfig(level="destructive")
        auth.confirm_destructive("destructive_tool", "10.0.0.1")
        agent = make_agent(tools=[DestructiveTool()], auth_config=auth)
        result = agent._execute_tool("destructive_tool", {"target": "10.0.0.1"})
        assert result == "destructive result"


class TestScopeEnforcement:
    def test_out_of_scope_denied(self, tmp_path):
        """Targets outside scope are denied."""
        scope_file = tmp_path / "scope.txt"
        scope_file.write_text("10.0.0.0/24\n")

        scope = ScopeConfig()
        scope.load(str(scope_file))

        agent = make_agent(tools=[PassiveTool()], scope_config=scope)
        result = agent._execute_tool("passive_tool", {"target": "192.168.1.1"})
        assert "outside" in result.lower() or "not in scope" in result.lower()

    def test_in_scope_allowed(self, tmp_path):
        """Targets within scope are allowed."""
        scope_file = tmp_path / "scope.txt"
        scope_file.write_text("10.0.0.0/24\n")

        scope = ScopeConfig()
        scope.load(str(scope_file))

        agent = make_agent(tools=[PassiveTool()], scope_config=scope)
        result = agent._execute_tool("passive_tool", {"target": "10.0.0.5"})
        assert result == "passive result"

    def test_no_scope_config_allows_all(self):
        """Without scope config, all targets allowed."""
        agent = make_agent(tools=[PassiveTool()], scope_config=None)
        result = agent._execute_tool("passive_tool", {"target": "8.8.8.8"})
        assert result == "passive result"

    def test_scope_not_loaded_allows_all(self):
        """ScopeConfig without loaded file allows all."""
        scope = ScopeConfig()  # not loaded
        agent = make_agent(tools=[PassiveTool()], scope_config=scope)
        result = agent._execute_tool("passive_tool", {"target": "8.8.8.8"})
        assert result == "passive result"


class TestToolCallLimit:
    def test_limit_reached_denies(self):
        """Tool calls beyond limit are denied."""
        agent = make_agent(tools=[PassiveTool()], max_tool_calls=3)

        # First 3 calls succeed
        for i in range(3):
            result = agent._execute_tool("passive_tool", {"target": "10.0.0.1"})
            assert result == "passive result"

        # 4th call denied
        result = agent._execute_tool("passive_tool", {"target": "10.0.0.1"})
        assert "limit" in result.lower()

    def test_limit_zero_means_unlimited(self):
        """max_tool_calls=0 disables the limit."""
        agent = make_agent(tools=[PassiveTool()], max_tool_calls=0)

        for i in range(10):
            result = agent._execute_tool("passive_tool", {"target": "10.0.0.1"})
            assert result == "passive result"

    def test_clear_session_resets_counter(self):
        """clear_session resets tool call count."""
        agent = make_agent(tools=[PassiveTool()], max_tool_calls=2)

        agent._execute_tool("passive_tool", {"target": "10.0.0.1"})
        agent._execute_tool("passive_tool", {"target": "10.0.0.1"})

        # Limit reached
        result = agent._execute_tool("passive_tool", {"target": "10.0.0.1"})
        assert "limit" in result.lower()

        # Reset
        agent.clear_session()

        # Works again
        result = agent._execute_tool("passive_tool", {"target": "10.0.0.1"})
        assert result == "passive result"


class TestFindingsIntegration:
    def test_findings_store_wired_to_tools(self, tmp_path):
        """FindingsStore is set on all tools."""
        db_path = str(tmp_path / "test.db")
        store = FindingsStore(db_path=db_path, retention_days=0)

        agent = make_agent(tools=[PassiveTool()], findings_store=store)

        tool = agent.tools_map["passive_tool"]
        assert tool._findings_store is store
        assert tool._current_session_id == agent.session_id

    def test_scan_run_recorded(self, tmp_path):
        """Tool execution records scan run in DB."""
        db_path = str(tmp_path / "test.db")
        store = FindingsStore(db_path=db_path, retention_days=0)

        agent = make_agent(tools=[PassiveTool()], findings_store=store)
        agent._execute_tool("passive_tool", {"target": "10.0.0.1"})

        runs = store.get_scan_runs(session_id=agent.session_id)
        assert len(runs) == 1
        assert runs[0].tool_name == "passive_tool"
        assert runs[0].target == "10.0.0.1"
        assert runs[0].status == "completed"

    def test_denied_scan_run_recorded(self, tmp_path):
        """Auth denial records scan run with DENIED status."""
        db_path = str(tmp_path / "test.db")
        store = FindingsStore(db_path=db_path, retention_days=0)
        auth = AuthorizationConfig(level="passive")

        agent = make_agent(tools=[ActiveTool()], auth_config=auth, findings_store=store)
        agent._execute_tool("active_tool", {"target": "10.0.0.1"})

        runs = store.get_scan_runs(session_id=agent.session_id)
        assert len(runs) == 1
        assert runs[0].status == "denied"

    def test_failed_scan_run_recorded(self, tmp_path):
        """Tool exception records scan run with failed status."""
        db_path = str(tmp_path / "test.db")
        store = FindingsStore(db_path=db_path, retention_days=0)

        agent = make_agent(tools=[ExceptionTool()], findings_store=store)
        agent._execute_tool("exception_tool", {"target": "10.0.0.1"})

        runs = store.get_scan_runs(session_id=agent.session_id)
        assert len(runs) == 1
        assert runs[0].status == "failed"

    def test_no_findings_store_works(self):
        """Everything works without FindingsStore (backward compatible)."""
        agent = make_agent(tools=[PassiveTool()], findings_store=None)
        result = agent._execute_tool("passive_tool", {"target": "10.0.0.1"})
        assert result == "passive result"


class TestTargetExtraction:
    def test_default_target_field(self):
        """Default target_fields=['target'] extracts target param."""
        agent = make_agent(tools=[PassiveTool()])
        tool = agent.tools_map["passive_tool"]
        target = agent._get_target_from_args(tool, {"target": "10.0.0.1"})
        assert target == "10.0.0.1"

    def test_no_target_returns_none(self):
        """Missing target field returns None."""
        agent = make_agent(tools=[PassiveTool()])
        tool = agent.tools_map["passive_tool"]
        target = agent._get_target_from_args(tool, {"other": "value"})
        assert target is None

    def test_custom_target_fields(self):
        """Tools with custom target_fields work."""

        class MultiTargetTool(BaseTool):
            def __init__(self):
                super().__init__()

            @property
            def name(self):
                return "multi_tool"

            @property
            def description(self):
                return "multi target"

            @property
            def parameters(self):
                return {"type": "object", "properties": {}}

            @property
            def target_fields(self):
                return ["network", "target"]

            def execute(self, **kwargs):
                return "ok"

        agent = make_agent(tools=[MultiTargetTool()])
        tool = agent.tools_map["multi_tool"]

        # "network" comes first in target_fields
        target = agent._get_target_from_args(
            tool, {"network": "10.0.0.0/24", "target": "10.0.0.1"}
        )
        assert target == "10.0.0.0/24"


class TestScanRunResetInFinally:
    def test_scan_run_reset_after_success(self, tmp_path):
        """Tool's _current_scan_run is None after successful execution."""
        db_path = str(tmp_path / "test.db")
        store = FindingsStore(db_path=db_path, retention_days=0)

        agent = make_agent(tools=[PassiveTool()], findings_store=store)
        agent._execute_tool("passive_tool", {"target": "10.0.0.1"})

        tool = agent.tools_map["passive_tool"]
        assert tool._current_scan_run is None

    def test_scan_run_reset_after_exception(self, tmp_path):
        """Tool's _current_scan_run is None after exception."""
        db_path = str(tmp_path / "test.db")
        store = FindingsStore(db_path=db_path, retention_days=0)

        agent = make_agent(tools=[ExceptionTool()], findings_store=store)
        agent._execute_tool("exception_tool", {"target": "10.0.0.1"})

        tool = agent.tools_map["exception_tool"]
        assert tool._current_scan_run is None
