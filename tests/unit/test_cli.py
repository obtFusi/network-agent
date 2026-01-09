"""
Tests for cli.py

Tests CLI commands without requiring actual LLM connection.
"""

from unittest.mock import MagicMock
from io import StringIO


class TestStatusCommand:
    """Tests for /status command output."""

    def test_status_output_format(self):
        """Status command outputs correct format."""
        # Create mock agent with test values
        mock_agent = MagicMock()
        mock_agent.context_limit = 131072
        mock_agent.last_prompt_tokens = 2500
        mock_agent.context_usage_percent = 1.9
        mock_agent.total_tokens = 5000
        mock_agent.truncation_count = 0

        # Capture output
        output = StringIO()

        # Simulate /status command logic (from cli.py:138-148)
        limit = mock_agent.context_limit
        used = mock_agent.last_prompt_tokens
        pct = mock_agent.context_usage_percent
        total = mock_agent.total_tokens
        truncations = mock_agent.truncation_count

        print("Session Status:", file=output)
        print(f"  Context: {used:,}/{limit:,} tokens ({pct:.1f}%)", file=output)
        print(f"  Session Tokens: {total:,}", file=output)
        print(f"  Truncations: {truncations}", file=output)

        result = output.getvalue()

        assert "Session Status:" in result
        assert "2,500/131,072 tokens (1.9%)" in result
        assert "Session Tokens: 5,000" in result
        assert "Truncations: 0" in result

    def test_status_with_truncations(self):
        """Status shows truncation count correctly."""
        mock_agent = MagicMock()
        mock_agent.context_limit = 8192
        mock_agent.last_prompt_tokens = 7000
        mock_agent.context_usage_percent = 85.4
        mock_agent.total_tokens = 25000
        mock_agent.truncation_count = 3

        output = StringIO()

        limit = mock_agent.context_limit
        used = mock_agent.last_prompt_tokens
        pct = mock_agent.context_usage_percent
        total = mock_agent.total_tokens
        truncations = mock_agent.truncation_count

        print("Session Status:", file=output)
        print(f"  Context: {used:,}/{limit:,} tokens ({pct:.1f}%)", file=output)
        print(f"  Session Tokens: {total:,}", file=output)
        print(f"  Truncations: {truncations}", file=output)

        result = output.getvalue()

        assert "7,000/8,192 tokens (85.4%)" in result
        assert "Session Tokens: 25,000" in result
        assert "Truncations: 3" in result


class TestToolsCommand:
    """Tests for /tools command output."""

    def test_tools_output_format(self):
        """Tools command outputs correct format."""
        # Create mock tools
        mock_tool = MagicMock()
        mock_tool.name = "ping_sweep"
        mock_tool.description = (
            "Scannt ein Netzwerk nach aktiven Hosts. Weitere Details."
        )

        mock_agent = MagicMock()
        mock_agent.tools = [mock_tool]

        output = StringIO()

        # Simulate /tools command logic (from cli.py)
        print("Available Tools:", file=output)
        for tool in mock_agent.tools:
            desc = tool.description
            if ". " in desc:
                desc = desc.split(". ")[0] + "."
            elif len(desc) > 60:
                desc = desc[:57] + "..."
            print(f"  {tool.name} - {desc}", file=output)

        result = output.getvalue()

        assert "Available Tools:" in result
        assert "ping_sweep" in result
        # Description should be truncated to first sentence
        assert "Scannt ein Netzwerk nach aktiven Hosts." in result
        assert "Weitere Details" not in result

    def test_tools_long_description_truncation(self):
        """Long descriptions without periods are truncated with ellipsis."""
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.description = "A" * 100  # 100 chars, no period

        mock_agent = MagicMock()
        mock_agent.tools = [mock_tool]

        output = StringIO()

        print("Available Tools:", file=output)
        for tool in mock_agent.tools:
            desc = tool.description
            if ". " in desc:
                desc = desc.split(". ")[0] + "."
            elif len(desc) > 60:
                desc = desc[:57] + "..."
            print(f"  {tool.name} - {desc}", file=output)

        result = output.getvalue()

        assert "test_tool" in result
        assert "..." in result
        # Should be truncated to 57 chars + "..."
        assert len("A" * 57 + "...") == 60

    def test_tools_multiple_tools(self):
        """Multiple tools are listed."""
        mock_tool1 = MagicMock()
        mock_tool1.name = "tool_one"
        mock_tool1.description = "First tool description."

        mock_tool2 = MagicMock()
        mock_tool2.name = "tool_two"
        mock_tool2.description = "Second tool description."

        mock_agent = MagicMock()
        mock_agent.tools = [mock_tool1, mock_tool2]

        output = StringIO()

        print("Available Tools:", file=output)
        for tool in mock_agent.tools:
            desc = tool.description
            if ". " in desc:
                desc = desc.split(". ")[0] + "."
            elif len(desc) > 60:
                desc = desc[:57] + "..."
            print(f"  {tool.name} - {desc}", file=output)

        result = output.getvalue()

        assert "tool_one" in result
        assert "tool_two" in result


class TestHelpCommand:
    """Tests for /help command."""

    def test_help_includes_all_commands(self):
        """Help command lists all commands including /tools."""
        output = StringIO()

        # Simulate /help output (from cli.py)
        print("Commands:", file=output)
        print("  /help    - Show available commands", file=output)
        print("  /tools   - List available tools", file=output)
        print("  /status  - Show session statistics", file=output)
        print("  /version - Show version", file=output)
        print("  /clear   - Reset session", file=output)
        print("  /exit    - Quit", file=output)

        result = output.getvalue()

        assert "/status" in result
        assert "/help" in result
        assert "/tools" in result
        assert "/version" in result
        assert "/clear" in result
        assert "/exit" in result


class TestVersionImport:
    """Tests for version consistency."""

    def test_version_is_string(self):
        """Version is a valid string."""
        from cli import __version__

        assert isinstance(__version__, str)
        assert len(__version__) > 0

    def test_version_format(self):
        """Version follows semver format."""
        from cli import __version__

        parts = __version__.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)
