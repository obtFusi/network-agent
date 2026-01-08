import json
from typing import Dict, Any, List
from agent.llm import LLMClient
from tools import get_all_tools


class NetworkAgent:
    """Agent mit Tool-Calling Loop und Session Memory"""

    # Truncation startet bei 80% des Context-Limits
    TRUNCATION_THRESHOLD = 0.8

    def __init__(self, config: Dict[str, Any], system_prompt: str):
        llm_config = config["llm"]["provider"]
        self.llm = LLMClient(
            model=llm_config["model"],
            base_url=llm_config["base_url"],
            temperature=llm_config["temperature"],
            max_tokens=llm_config["max_tokens"],
            max_context_tokens=llm_config.get("max_context_tokens")
        )

        self.tools = get_all_tools()
        self.tools_map = {tool.name: tool for tool in self.tools}
        self.tools_schema = [tool.to_openai_format() for tool in self.tools]

        self.system_prompt = system_prompt
        self.max_iterations = config["agent"]["max_iterations"]
        self.verbose = config["agent"]["verbose"]

        # Session Memory - Messages bleiben zwischen run() Aufrufen erhalten
        self.messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt}
        ]

        # Token tracking
        self.total_tokens = 0
        self.last_usage = None
        self.last_prompt_tokens = 0
        self.truncation_count = 0  # Wie oft wurde truncated

    @property
    def context_limit(self) -> int:
        """Context-Limit vom LLM Wrapper"""
        return self.llm.get_context_limit()

    @property
    def context_usage_percent(self) -> float:
        """Aktuelle Context-Auslastung in Prozent"""
        if self.last_prompt_tokens == 0:
            return 0.0
        return (self.last_prompt_tokens / self.context_limit) * 100

    def clear_session(self) -> None:
        """Setzt Session zurück (behält nur System-Prompt)"""
        self.messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        self.total_tokens = 0
        self.last_usage = None
        self.last_prompt_tokens = 0
        self.truncation_count = 0

    def _truncate_if_needed(self) -> bool:
        """Entfernt älteste Nachrichten wenn Context-Limit naht.

        Returns:
            True wenn truncation durchgeführt wurde
        """
        threshold = int(self.context_limit * self.TRUNCATION_THRESHOLD)

        if self.last_prompt_tokens < threshold:
            return False

        # Truncation nötig - entferne älteste User/Assistant Paare
        # System-Prompt (Index 0) bleibt immer
        truncated = False

        while self.last_prompt_tokens >= threshold and len(self.messages) > 2:
            # Finde erstes User/Assistant Paar nach System-Prompt
            # und entferne es samt zugehöriger Tool-Results
            removed_count = 0

            # Entferne Messages bis zum nächsten User-Turn (oder Ende)
            i = 1
            while i < len(self.messages):
                msg = self.messages[i]
                if msg["role"] == "user" and removed_count > 0:
                    # Nächster User-Turn erreicht, aufhören
                    break
                self.messages.pop(i)
                removed_count += 1
                truncated = True

            if removed_count == 0:
                break

            # Schätze neue Token-Anzahl (grob: proportional zur Nachrichtenanzahl)
            # Genauer Wert kommt erst nach dem nächsten API-Call
            ratio = len(self.messages) / (len(self.messages) + removed_count)
            self.last_prompt_tokens = int(self.last_prompt_tokens * ratio)

        if truncated:
            self.truncation_count += 1

        return truncated

    def run(self, user_input: str) -> str:
        """Führt Agent-Loop aus mit Session Memory"""

        # Truncation prüfen BEVOR neue Message hinzugefügt wird
        was_truncated = self._truncate_if_needed()
        if was_truncated and self.verbose:
            print("[Session Memory: Ältere Nachrichten entfernt]")

        # Neue User-Message zur Session hinzufügen
        self.messages.append({"role": "user", "content": user_input})

        for iteration in range(self.max_iterations):
            if self.verbose:
                print(f"\n[Iteration {iteration + 1}]")

            # LLM aufrufen
            response = self.llm.chat(self.messages, tools=self.tools_schema)
            message = response.choices[0].message

            # Token usage tracken
            if hasattr(response, 'usage') and response.usage:
                self.last_usage = response.usage
                self.last_prompt_tokens = response.usage.prompt_tokens
                self.total_tokens += response.usage.total_tokens

            # Keine Tool-Calls? → Fertig
            if not message.tool_calls:
                # Assistant-Antwort zur Session hinzufügen
                self.messages.append({
                    "role": "assistant",
                    "content": message.content
                })
                return message.content

            # Tool-Calls vorhanden - Message zur Session hinzufügen
            self.messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]
            })

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

                # Tool-Result zur Session hinzufügen
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

        return "Error: Max iterations reached"
