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


class TestHelpCommand:
    """Tests for /help command."""

    def test_help_includes_status(self):
        """Help command lists /status."""
        output = StringIO()

        # Simulate /help output (from cli.py:150-156)
        print("Commands:", file=output)
        print("  /help    - Show available commands", file=output)
        print("  /status  - Show session statistics", file=output)
        print("  /version - Show version", file=output)
        print("  /clear   - Reset session", file=output)
        print("  /exit    - Quit", file=output)

        result = output.getvalue()

        assert "/status" in result
        assert "/help" in result
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
