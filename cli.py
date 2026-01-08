import yaml
from pathlib import Path
from dotenv import load_dotenv
from agent.core import NetworkAgent


def main():
    # Load environment variables
    load_dotenv()

    # Load config
    config_path = Path("config/settings.yaml")
    config = yaml.safe_load(config_path.read_text())

    # Load system prompt
    system_prompt_path = Path("config/prompts/system.md")
    system_prompt = system_prompt_path.read_text()

    # Initialize agent
    print("Network Agent startet...")
    print(f"   Model: {config['llm']['venice']['model']}")
    print("   Type 'exit' or 'quit' to stop\n")

    agent = NetworkAgent(config, system_prompt)

    # REPL Loop
    while True:
        try:
            user_input = input("\n> ")

            if user_input.lower() in ["exit", "quit", "q"]:
                print("Bye!")
                break

            if not user_input.strip():
                continue

            response = agent.run(user_input)
            print(f"\n{response}")

        except KeyboardInterrupt:
            print("\n\nBye!")
            break
        except Exception as e:
            print(f"\nError: {e}")


if __name__ == "__main__":
    main()
