"""
Tests for cli.py

Tests CLI functions directly - no code copying!
Uses real functions from cli.py and real tools from tools/.
"""

from cli import truncate_description, get_help_text, get_tools_text, __version__
from tools import get_all_tools


class TestTruncateDescription:
    """Tests for truncate_description() function."""

    def test_empty_string(self):
        """Empty input returns empty output."""
        assert truncate_description("") == ""

    def test_none_input(self):
        """None input returns empty output."""
        assert truncate_description(None) == ""

    def test_short_string_unchanged(self):
        """Short string without period stays unchanged."""
        assert truncate_description("Hello world") == "Hello world"

    def test_truncates_at_first_sentence(self):
        """String is truncated at first sentence end."""
        result = truncate_description("First sentence. Second sentence.")
        assert result == "First sentence."

    def test_long_string_truncated_with_ellipsis(self):
        """Long string without period gets ellipsis."""
        long_text = "A" * 100
        result = truncate_description(long_text)
        assert result == "A" * 57 + "..."
        assert len(result) == 60

    def test_custom_max_length(self):
        """Custom max_length is respected."""
        result = truncate_description("A" * 50, max_length=30)
        assert result == "A" * 27 + "..."
        assert len(result) == 30

    def test_sentence_takes_priority_over_length(self):
        """First sentence is kept even if short."""
        result = truncate_description("Hi. This is longer text here.")
        assert result == "Hi."

    def test_exact_max_length_no_truncation(self):
        """String at exactly max_length stays unchanged."""
        text = "A" * 60
        result = truncate_description(text, max_length=60)
        assert result == text


class TestGetHelpText:
    """Golden tests for get_help_text() output."""

    def test_help_text_contains_all_commands(self):
        """Help text includes all expected commands."""
        help_text = get_help_text()

        # All commands must be present
        assert "/help" in help_text
        assert "/tools" in help_text
        assert "/config" in help_text
        assert "/status" in help_text
        assert "/version" in help_text
        assert "/clear" in help_text
        assert "/exit" in help_text

    def test_help_text_starts_with_commands(self):
        """Help text starts with 'Commands:' header."""
        help_text = get_help_text()
        assert help_text.startswith("Commands:")

    def test_help_text_stable_format(self):
        """Help text format is stable (golden test)."""
        help_text = get_help_text()

        # Exact expected output - if this fails, update intentionally
        expected = """Commands:
  /help    - Show available commands
  /tools   - List available tools
  /config  - Show LLM configuration
  /status  - Show session statistics
  /version - Show version
  /clear   - Reset session
  /exit    - Quit"""

        assert help_text == expected


class TestGetToolsText:
    """Tests for get_tools_text() - tests REAL tools!"""

    def test_tools_text_starts_with_header(self):
        """Tools text starts with 'Available Tools:' header."""
        tools_text = get_tools_text()
        assert tools_text.startswith("Available Tools:")

    def test_tools_text_contains_ping_sweep(self):
        """Tools text contains ping_sweep tool."""
        tools_text = get_tools_text()
        assert "ping_sweep" in tools_text

    def test_tools_text_has_descriptions(self):
        """Each tool line has a description after the dash."""
        tools_text = get_tools_text()
        lines = tools_text.split("\n")

        # Skip header line
        tool_lines = [line for line in lines[1:] if line.strip()]

        for line in tool_lines:
            assert " - " in line, f"Tool line missing description separator: {line}"

    def test_tools_text_matches_registry(self):
        """Tools text contains all tools from registry."""
        tools_text = get_tools_text()
        tools = get_all_tools()

        for tool in tools:
            assert tool.name in tools_text, f"Tool {tool.name} not in output"


class TestGetAllToolsContract:
    """Contract tests for get_all_tools() registry."""

    def test_returns_list(self):
        """Registry returns a list."""
        tools = get_all_tools()
        assert isinstance(tools, list)

    def test_not_empty(self):
        """Registry is not empty."""
        tools = get_all_tools()
        assert len(tools) > 0

    def test_all_tools_have_name(self):
        """All tools have a non-empty name."""
        tools = get_all_tools()
        for tool in tools:
            assert hasattr(tool, "name"), "Tool missing 'name' attribute"
            assert tool.name, "Tool has empty name"
            assert isinstance(tool.name, str), f"Tool name is not string: {tool.name}"

    def test_all_tools_have_description(self):
        """All tools have a non-empty description."""
        tools = get_all_tools()
        for tool in tools:
            assert hasattr(tool, "description"), (
                f"Tool {tool.name} missing 'description'"
            )
            assert tool.description, f"Tool {tool.name} has empty description"
            assert isinstance(tool.description, str), (
                f"Tool {tool.name} description is not string"
            )

    def test_all_tools_have_parameters(self):
        """All tools have a parameters schema."""
        tools = get_all_tools()
        for tool in tools:
            assert hasattr(tool, "parameters"), f"Tool {tool.name} missing 'parameters'"
            assert isinstance(tool.parameters, dict), (
                f"Tool {tool.name} parameters is not dict"
            )

    def test_all_tools_have_execute(self):
        """All tools have an execute method."""
        tools = get_all_tools()
        for tool in tools:
            assert hasattr(tool, "execute"), (
                f"Tool {tool.name} missing 'execute' method"
            )
            assert callable(tool.execute), f"Tool {tool.name} execute is not callable"

    def test_no_duplicate_names(self):
        """All tool names are unique."""
        tools = get_all_tools()
        names = [tool.name for tool in tools]
        assert len(names) == len(set(names)), f"Duplicate tool names: {names}"


class TestVersion:
    """Tests for version consistency."""

    def test_version_is_string(self):
        """Version is a valid string."""
        assert isinstance(__version__, str)
        assert len(__version__) > 0

    def test_version_format(self):
        """Version follows semver format (X.Y.Z)."""
        parts = __version__.split(".")
        assert len(parts) == 3, f"Version {__version__} is not semver"
        assert all(part.isdigit() for part in parts), (
            f"Version {__version__} has non-numeric parts"
        )


class TestCLIArguments:
    """Integration tests for CLI arguments."""

    def test_help_commands_argument(self):
        """--help-commands outputs help text and exits."""
        import subprocess
        import sys
        from pathlib import Path

        project_root = Path(__file__).parent.parent.parent
        result = subprocess.run(
            [sys.executable, "cli.py", "--help-commands"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )

        assert result.returncode == 0
        assert "Commands:" in result.stdout
        assert "/help" in result.stdout

    def test_list_tools_argument(self):
        """--list-tools outputs tools and exits."""
        import subprocess
        import sys
        from pathlib import Path

        project_root = Path(__file__).parent.parent.parent
        result = subprocess.run(
            [sys.executable, "cli.py", "--list-tools"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )

        assert result.returncode == 0
        assert "Available Tools:" in result.stdout
        assert "ping_sweep" in result.stdout

    def test_version_argument(self):
        """--version outputs version and exits."""
        import subprocess
        import sys
        from pathlib import Path

        project_root = Path(__file__).parent.parent.parent
        result = subprocess.run(
            [sys.executable, "cli.py", "--version"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )

        assert result.returncode == 0
        assert __version__ in result.stdout
