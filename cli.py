import argparse
import os
import sys
import yaml
from pathlib import Path
from dotenv import load_dotenv

__version__ = "0.3.6"


def truncate_description(desc: str, max_length: int = 60) -> str:
    """Kürzt eine Beschreibung auf den ersten Satz oder max_length Zeichen.

    Args:
        desc: Die zu kürzende Beschreibung
        max_length: Maximale Länge (default: 60)

    Returns:
        Gekürzte Beschreibung
    """
    if not desc:
        return ""
    if ". " in desc:
        return desc.split(". ")[0] + "."
    if len(desc) > max_length:
        return desc[: max_length - 3] + "..."
    return desc


def get_help_text() -> str:
    """Gibt den Hilfetext für alle Commands zurück."""
    return """Commands:
  /help    - Show available commands
  /tools   - List available tools
  /config  - Show LLM configuration
  /status  - Show session statistics
  /version - Show version
  /clear   - Reset session
  /exit    - Quit"""


def get_tools_text() -> str:
    """Gibt die Liste aller Tools zurück (ohne Agent-Initialisierung)."""
    from tools import get_all_tools

    lines = ["Available Tools:"]
    for tool in get_all_tools():
        desc = truncate_description(tool.description)
        lines.append(f"  {tool.name} - {desc}")
    return "\n".join(lines)


def check_setup() -> tuple[bool, list[str]]:
    """Prüft ob alle erforderlichen Konfigurationen vorhanden sind.

    Returns:
        (is_configured, missing_items)
    """
    missing = []

    # Config laden
    config_path = Path("config/settings.yaml")
    config = yaml.safe_load(config_path.read_text())
    provider = config.get("llm", {}).get("provider", {})

    # Pflichtfelder prüfen
    if not provider.get("model"):
        missing.append("model in config/settings.yaml")
    if not provider.get("base_url"):
        missing.append("base_url in config/settings.yaml")
    if not os.getenv("LLM_API_KEY"):
        missing.append("LLM_API_KEY in .env")

    return (len(missing) == 0, missing)


def show_setup_guide(missing: list[str]):
    """Zeigt Setup-Anleitung für fehlende Konfiguration."""
    print("=" * 60)
    print("Network Agent - Setup erforderlich")
    print("=" * 60)
    print()
    print("Folgende Konfiguration fehlt:")
    for item in missing:
        print(f"  - {item}")
    print()
    print("-" * 60)
    print("SETUP-ANLEITUNG:")
    print("-" * 60)
    print()
    print("1. API Key einrichten:")
    print("   cp .env.example .env")
    print("   # Dann .env bearbeiten und Key eintragen:")
    print("   LLM_API_KEY=dein_api_key_hier")
    print()
    print("2. Provider konfigurieren (config/settings.yaml):")
    print()
    print("   Für OpenAI:")
    print('     model: "gpt-4"')
    print('     base_url: "https://api.openai.com/v1"')
    print()
    print("   Für Groq (kostenlos):")
    print('     model: "llama-3.3-70b-versatile"')
    print('     base_url: "https://api.groq.com/openai/v1"')
    print()
    print("   Für Ollama (lokal):")
    print('     model: "llama3"')
    print('     base_url: "http://localhost:11434/v1"')
    print()
    print("Mehr Provider: siehe README.md")
    print("=" * 60)


def main():
    # Argument parsing
    parser = argparse.ArgumentParser(
        description="Network Agent - KI-gesteuerter Netzwerk-Scanner"
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
    args = parser.parse_args()

    # Commands die OHNE LLM-Setup funktionieren
    if args.help_commands:
        print(get_help_text())
        sys.exit(0)

    if args.list_tools:
        print(get_tools_text())
        sys.exit(0)

    # Load environment variables
    load_dotenv()

    # Setup-Check (nur für interaktiven Modus)
    is_configured, missing = check_setup()
    if not is_configured:
        show_setup_guide(missing)
        sys.exit(1)

    # Ab hier: Alles konfiguriert, Agent starten
    from agent.core import NetworkAgent

    # Load config
    config_path = Path("config/settings.yaml")
    config = yaml.safe_load(config_path.read_text())

    # Load system prompt
    system_prompt_path = Path("config/prompts/system.md")
    system_prompt = system_prompt_path.read_text()

    # Initialize agent
    print("Network Agent startet...")
    print(f"   Model: {config['llm']['provider']['model']}")

    agent = NetworkAgent(config, system_prompt)

    # Context-Limit anzeigen
    print(f"   Context-Limit: {agent.context_limit:,} tokens")
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
                    print("[Session zurückgesetzt]")
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

            # Token usage anzeigen
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
