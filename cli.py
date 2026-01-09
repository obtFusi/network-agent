import argparse
import os
import sys
import yaml
from pathlib import Path
from dotenv import load_dotenv

__version__ = "0.3.3"


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
    print("     model: \"gpt-4\"")
    print("     base_url: \"https://api.openai.com/v1\"")
    print()
    print("   Für Groq (kostenlos):")
    print("     model: \"llama-3.3-70b-versatile\"")
    print("     base_url: \"https://api.groq.com/openai/v1\"")
    print()
    print("   Für Ollama (lokal):")
    print("     model: \"llama3\"")
    print("     base_url: \"http://localhost:11434/v1\"")
    print()
    print("Mehr Provider: siehe README.md")
    print("=" * 60)


def main():
    # Argument parsing
    parser = argparse.ArgumentParser(
        description="Network Agent - KI-gesteuerter Netzwerk-Scanner"
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"Network Agent v{__version__}"
    )
    parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Setup-Check
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

                if cmd == "/help":
                    print("Commands:")
                    print("  /help    - Show available commands")
                    print("  /version - Show version")
                    print("  /clear   - Reset session")
                    print("  /exit    - Quit")
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
