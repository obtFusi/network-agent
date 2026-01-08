import json
from typing import Dict, Any
from agent.llm import VeniceLLM
from tools import get_all_tools


class NetworkAgent:
    """Agent mit Tool-Calling Loop"""

    def __init__(self, config: Dict[str, Any], system_prompt: str):
        self.llm = VeniceLLM(
            model=config["llm"]["venice"]["model"],
            temperature=config["llm"]["venice"]["temperature"],
            max_tokens=config["llm"]["venice"]["max_tokens"]
        )

        self.tools = get_all_tools()
        self.tools_map = {tool.name: tool for tool in self.tools}
        self.tools_schema = [tool.to_openai_format() for tool in self.tools]

        self.system_prompt = system_prompt
        self.max_iterations = config["agent"]["max_iterations"]
        self.verbose = config["agent"]["verbose"]

        # Token tracking
        self.total_tokens = 0
        self.last_usage = None

    def run(self, user_input: str) -> str:
        """Führt Agent-Loop aus"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input}
        ]

        for iteration in range(self.max_iterations):
            if self.verbose:
                print(f"\n[Iteration {iteration + 1}]")

            # LLM aufrufen
            response = self.llm.chat(messages, tools=self.tools_schema)
            message = response.choices[0].message

            # Token usage tracken
            if hasattr(response, 'usage') and response.usage:
                self.last_usage = response.usage
                self.total_tokens += response.usage.total_tokens

            # Keine Tool-Calls? → Fertig
            if not message.tool_calls:
                return message.content

            # Tool-Calls vorhanden
            messages.append(message)

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                if self.verbose:
                    print(f"  Tool: {tool_name}({tool_args})")

                # Tool ausführen
                if tool_name in self.tools_map:
                    result = self.tools_map[tool_name].execute(**tool_args)
                else:
                    result = f"Error: Tool {tool_name} not found"

                if self.verbose:
                    print(f"  Result: {result[:100]}...")

                # Tool-Result zu Messages hinzufügen
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

        return "Error: Max iterations reached"
