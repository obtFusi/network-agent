import argparse
import os
import sys
import yaml
from pathlib import Path
from dotenv import load_dotenv

__version__ = "0.13.0"


def truncate_description(desc: str, max_length: int = 60) -> str:
    """Truncate description to first sentence or max_length characters.

    Args:
        desc: Description to truncate
        max_length: Maximum length (default: 60)

    Returns:
        Truncated description
    """
    if not desc:
        return ""
    if ". " in desc:
        return desc.split(". ")[0] + "."
    if len(desc) > max_length:
        return desc[: max_length - 3] + "..."
    return desc


def get_help_text() -> str:
    """Return help text for all commands."""
    return """Commands:
  /help    - Show available commands
  /tools   - List available tools
  /config  - Show LLM configuration
  /status  - Show session statistics
  /version - Show version
  /clear   - Reset session
  /exit    - Quit"""


def get_tools_text() -> str:
    """Return list of all tools (without agent initialization)."""
    from tools import get_all_tools

    lines = ["Available Tools:"]
    for tool in get_all_tools():
        desc = truncate_description(tool.description)
        lines.append(f"  {tool.name} - {desc}")
    return "\n".join(lines)


def check_setup() -> tuple[bool, list[str]]:
    """Check if all required configurations are present.

    Returns:
        (is_configured, missing_items)
    """
    missing = []

    # Load config
    config_path = Path("config/settings.yaml")
    config = yaml.safe_load(config_path.read_text())
    provider = config.get("llm", {}).get("provider", {})

    # Check required fields
    if not provider.get("model"):
        missing.append("model in config/settings.yaml")
    if not provider.get("base_url"):
        missing.append("base_url in config/settings.yaml")
    if not os.getenv("LLM_API_KEY"):
        missing.append("LLM_API_KEY in .env")

    return (len(missing) == 0, missing)


def show_setup_guide(missing: list[str]):
    """Show setup guide for missing configuration."""
    print("=" * 60)
    print("Network Agent - Setup Required")
    print("=" * 60)
    print()
    print("Missing configuration:")
    for item in missing:
        print(f"  - {item}")
    print()
    print("-" * 60)
    print("SETUP GUIDE:")
    print("-" * 60)
    print()
    print("1. Set up API key:")
    print("   cp .env.example .env")
    print("   # Then edit .env and add your key:")
    print("   LLM_API_KEY=your_api_key_here")
    print()
    print("2. Configure provider (config/settings.yaml):")
    print()
    print("   For OpenAI:")
    print('     model: "gpt-4"')
    print('     base_url: "https://api.openai.com/v1"')
    print()
    print("   For Groq (free):")
    print('     model: "llama-3.3-70b-versatile"')
    print('     base_url: "https://api.groq.com/openai/v1"')
    print()
    print("   For Ollama (local):")
    print('     model: "llama3"')
    print('     base_url: "http://localhost:11434/v1"')
    print()
    print("More providers: see README.md")
    print("=" * 60)


def main():
    # Argument parsing
    parser = argparse.ArgumentParser(
        description="Network Agent - AI-powered network scanner"
    )
    parser.add_argument(
        "--version", "-v", action="version", version=f"Network Agent v{__version__}"
    )
    parser.add_argument(
        "--help-commands", action="store_true", help="Show available REPL commands"
    )
    parser.add_argument(
        "--list-tools", action="store_true", help="List available tools"
    )
    parser.add_argument(
        "--serve", action="store_true", help="Start HTTP API server instead of REPL"
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="API server host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="API server port (default: 8080)"
    )
    parser.add_argument(
        "--i-have-written-authorization",
        action="store_true",
        help="Enable active/destructive tools (requires written pentest authorization)",
    )
    parser.add_argument(
        "--findings-db",
        default=None,
        help="Path to findings database (default: data/findings.db)",
    )
    parser.add_argument(
        "--export",
        choices=["json", "csv", "html"],
        default=None,
        help="Export findings report in specified format and exit",
    )
    parser.add_argument(
        "--scope-file",
        default=None,
        help="Path to scope file with allowed CIDR ranges and hostnames",
    )
    args = parser.parse_args()

    # Commands that work WITHOUT LLM setup
    if args.help_commands:
        print(get_help_text())
        sys.exit(0)

    if args.list_tools:
        print(get_tools_text())
        sys.exit(0)

    # Load environment variables
    load_dotenv()

    # Setup check (only for interactive mode)
    is_configured, missing = check_setup()
    if not is_configured:
        show_setup_guide(missing)
        sys.exit(1)

    # From here: All configured, start agent

    # Load config
    config_path = Path("config/settings.yaml")
    config = yaml.safe_load(config_path.read_text())

    # Load system prompt
    system_prompt_path = Path("config/prompts/system.md")
    system_prompt = system_prompt_path.read_text()

    # HTTP API Server mode
    if args.serve:
        import uvicorn
        from agent.api import create_app
        from tools.findings_store import FindingsStore

        # Initialize findings store for API
        findings_config = config.get("findings", {})
        api_findings_store = None
        if findings_config.get("enabled", True):
            db_path = args.findings_db or findings_config.get(
                "db_path", "data/findings.db"
            )
            api_findings_store = FindingsStore(
                db_path=db_path,
                store_raw_output=findings_config.get("store_raw_output", False),
                max_output_size=findings_config.get("max_output_size", 10000),
                strict=findings_config.get("strict", False),
                retention_days=findings_config.get("retention_days", 90),
            )

        print("Network Agent API Server starting...")
        print(f"   Model: {config['llm']['provider']['model']}")
        print(f"   Host: {args.host}")
        print(f"   Port: {args.port}")
        print(f"   Docs: http://{args.host}:{args.port}/docs")

        app = create_app(config, system_prompt, findings_store=api_findings_store)
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
        sys.exit(0)

    # Export mode (no LLM needed)
    if args.export:
        from tools.findings_store import FindingsStore
        from tools.findings_export import export_json, export_csv, export_html

        db_path = args.findings_db or config.get("findings", {}).get(
            "db_path", "data/findings.db"
        )
        store = FindingsStore(db_path=db_path, retention_days=0)

        output_path = f"findings_report.{args.export}"
        exporters = {"json": export_json, "csv": export_csv, "html": export_html}
        result_path = exporters[args.export](store, output_path)
        print(f"Report exported: {result_path}")
        print(f"Integrity file: {result_path}.sha256")
        sys.exit(0)

    # REPL mode
    from agent.core import NetworkAgent
    from tools.authorization import AuthorizationConfig
    from tools.findings_store import FindingsStore
    from tools.scope import ScopeConfig

    # Authorization setup
    auth_level = "passive"
    if args.i_have_written_authorization:
        auth_level = "active"
    # Config can override (CLI flag takes precedence if set)
    config_auth = config.get("scan", {}).get("authorization_level")
    if config_auth and not args.i_have_written_authorization:
        auth_level = config_auth
    elif args.i_have_written_authorization:
        auth_level = "active"

    auth_config = AuthorizationConfig(level=auth_level)

    # Findings DB setup
    findings_config = config.get("findings", {})
    findings_enabled = findings_config.get("enabled", True)
    findings_store = None
    if findings_enabled:
        db_path = args.findings_db or findings_config.get("db_path", "data/findings.db")
        findings_store = FindingsStore(
            db_path=db_path,
            store_raw_output=findings_config.get("store_raw_output", False),
            max_output_size=findings_config.get("max_output_size", 10000),
            strict=findings_config.get("strict", False),
            retention_days=findings_config.get("retention_days", 90),
        )

    # Scope enforcement setup
    scope_config = None
    if args.scope_file:
        scope_config = ScopeConfig()
        scope_config.load(args.scope_file)
        print(f"   Scope file loaded: {args.scope_file}")

    # Initialize agent
    print("Network Agent starting...")
    print(f"   Model: {config['llm']['provider']['model']}")
    print(f"   Authorization: {auth_level}")

    agent = NetworkAgent(
        config,
        system_prompt,
        auth_config=auth_config,
        findings_store=findings_store,
        scope_config=scope_config,
    )

    # Show context limit
    print(f"   Context limit: {agent.context_limit:,} tokens")
    print("   Type /help for available commands\n")

    # REPL Loop
    while True:
        try:
            user_input = input("\n> ")

            # Empty input
            if not user_input.strip():
                continue

            # Slash commands
            if user_input.startswith("/"):
                cmd = user_input.lower().strip()

                if cmd == "/exit":
                    print("Bye!")
                    break

                if cmd == "/clear":
                    agent.clear_session()
                    print("[Session reset]")
                    continue

                if cmd == "/version":
                    print(f"Network Agent v{__version__}")
                    continue

                if cmd == "/status":
                    limit = agent.context_limit
                    used = agent.last_prompt_tokens
                    pct = agent.context_usage_percent
                    total = agent.total_tokens
                    truncations = agent.truncation_count
                    print("Session Status:")
                    print(f"  Context: {used:,}/{limit:,} tokens ({pct:.1f}%)")
                    print(f"  Session Tokens: {total:,}")
                    print(f"  Truncations: {truncations}")
                    continue

                if cmd == "/tools":
                    print(get_tools_text())
                    continue

                if cmd == "/config":
                    print("LLM Configuration:")
                    print(f"  Model: {agent.llm.model}")
                    print(f"  Base URL: {agent.llm.base_url}")
                    print(f"  Context Limit: {agent.context_limit:,} tokens")
                    continue

                if cmd == "/help":
                    print(get_help_text())
                    continue

                # Unknown slash command
                print(f"Unknown command: {user_input.split()[0]} (try /help)")
                continue

            # Normal text -> send to LLM
            response = agent.run(user_input)
            print(f"\n{response}")

            # Show token usage
            if agent.last_usage:
                pct = agent.context_usage_percent
                limit = agent.context_limit
                print(
                    f"\n[{agent.last_prompt_tokens:,}/{limit:,} tokens ({pct:.1f}%) | "
                    f"Session: {agent.total_tokens:,}]"
                )

        except KeyboardInterrupt:
            print("\n\nBye!")
            break
        except EOFError:
            print("\nBye!")
            break
        except Exception as e:
            print(f"\nError: {e}")


if __name__ == "__main__":
    main()
