import json
import logging
import sys
import uuid
from typing import Any, Dict, List, Optional

from agent.llm import LLMClient
from tools import get_all_tools
from tools.authorization import AuthorizationConfig
from tools.base import ToolResult
from tools.findings_store import FindingsStore, ScanStatus
from tools.scope import ScopeConfig

logger = logging.getLogger(__name__)


class NetworkAgent:
    """Agent mit Tool-Calling Loop und Session Memory"""

    # Truncation startet bei 80% des Context-Limits
    TRUNCATION_THRESHOLD = 0.8

    def __init__(
        self,
        config: Dict[str, Any],
        system_prompt: str,
        auth_config: Optional[AuthorizationConfig] = None,
        findings_store: Optional[FindingsStore] = None,
        scope_config: Optional[ScopeConfig] = None,
    ):
        llm_config = config["llm"]["provider"]
        ollama_config = config["llm"].get("ollama", {})
        self.llm = LLMClient(
            model=llm_config["model"],
            base_url=llm_config["base_url"],
            temperature=llm_config["temperature"],
            max_tokens=llm_config["max_tokens"],
            max_context_tokens=llm_config.get("max_context_tokens"),
            ollama_options=ollama_config if ollama_config else None,
        )

        self.tools = get_all_tools()
        self.tools_map = {tool.name: tool for tool in self.tools}
        self.tools_schema = [tool.to_openai_format() for tool in self.tools]

        self.system_prompt = system_prompt
        self.max_iterations = config["agent"]["max_iterations"]
        self.verbose = config["agent"]["verbose"]

        # Authorization, Findings, Scope
        self._auth_config = auth_config
        self._findings_store = findings_store
        self._scope_config = scope_config

        # Session ID for findings tracking
        self.session_id = str(uuid.uuid4())

        # Tool-call safety limit
        scan_config = config.get("scan", {})
        self._max_tool_calls = scan_config.get("max_tool_calls", 200)
        self._tool_call_count = 0

        # Wire up findings store to tools
        if self._findings_store:
            for tool in self.tools:
                tool._findings_store = self._findings_store
                tool._current_session_id = self.session_id

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
        self.messages = [{"role": "system", "content": self.system_prompt}]
        self.total_tokens = 0
        self.last_usage = None
        self.last_prompt_tokens = 0
        self.truncation_count = 0
        self._tool_call_count = 0

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

    def _get_target_from_args(self, tool, tool_args: dict) -> Optional[str]:
        """Extract the primary target from tool arguments using target_fields."""
        for field_name in tool.target_fields:
            if field_name in tool_args:
                return str(tool_args[field_name])
        return None

    def _execute_tool(self, tool_name: str, tool_args: dict) -> str:
        """Execute a single tool with authorization, scope, and findings checks.

        Returns the result string to send back to the LLM.
        """
        # Tool-call safety limit
        self._tool_call_count += 1
        if self._max_tool_calls > 0 and self._tool_call_count > self._max_tool_calls:
            return (
                f"Error: Tool call limit ({self._max_tool_calls}) reached. "
                "Use /clear to reset the session."
            )

        # Tool lookup
        if tool_name not in self.tools_map:
            return f"Error: Tool {tool_name} not found"

        tool = self.tools_map[tool_name]
        target = self._get_target_from_args(tool, tool_args)
        scan_run_id = None

        try:
            # Authorization check
            if self._auth_config:
                allowed, msg = self._auth_config.check(
                    tool_name, tool.authorization_level
                )
                if not allowed:
                    self._record_denied(tool_name, target or "unknown", tool_args, msg)
                    return msg

                # Destructive confirmation check
                if tool.authorization_level == "destructive" and target:
                    if self._auth_config.requires_confirmation(tool_name, target):
                        if not sys.stdin.isatty():
                            deny_msg = (
                                f"Destructive tool '{tool_name}' denied: "
                                "non-interactive mode (no TTY)."
                            )
                            self._record_denied(tool_name, target, tool_args, deny_msg)
                            return deny_msg

                        # Human-in-the-Loop CLI prompt
                        try:
                            confirm = input(
                                f"\n[DESTRUCTIVE] Execute '{tool_name}' on '{target}'? "
                                "Type 'yes' to confirm: "
                            )
                            if confirm.strip().lower() != "yes":
                                deny_msg = (
                                    f"Destructive tool '{tool_name}' cancelled by user."
                                )
                                self._record_denied(
                                    tool_name, target, tool_args, deny_msg
                                )
                                return deny_msg
                            self._auth_config.confirm_destructive(tool_name, target)
                        except (EOFError, KeyboardInterrupt):
                            deny_msg = f"Destructive tool '{tool_name}' cancelled (input interrupted)."
                            self._record_denied(tool_name, target, tool_args, deny_msg)
                            return deny_msg

            # Scope check
            if self._scope_config and self._scope_config.is_loaded and target:
                in_scope, scope_msg = self._scope_config.is_in_scope(target)
                if not in_scope:
                    self._record_denied(tool_name, target, tool_args, scope_msg)
                    return scope_msg

            # Record scan run start
            scan_run_id = self._start_scan_run(tool_name, target, tool_args)

            # Set current scan run on tool for findings tracking
            if scan_run_id:
                tool._current_scan_run = scan_run_id

            # Execute tool
            raw_result = tool.execute(**tool_args)

            # Adapt result
            if isinstance(raw_result, ToolResult):
                tool_result = raw_result
            else:
                # Legacy: str -> ToolResult
                if isinstance(raw_result, str) and (
                    raw_result.startswith("Error:")
                    or raw_result.startswith("Validation error:")
                ):
                    error_type = (
                        "validation" if "Validation" in raw_result else "runtime"
                    )
                    tool_result = ToolResult(
                        status="failed", message=raw_result, error_type=error_type
                    )
                else:
                    tool_result = ToolResult(
                        status="completed",
                        message=raw_result
                        if isinstance(raw_result, str)
                        else str(raw_result),
                    )

            # Record scan run completion
            self._complete_scan_run(
                scan_run_id, tool_result.status, tool_result.message
            )

            return tool_result.message

        except Exception as e:
            error_msg = f"Error: Tool execution failed: {e}"
            self._complete_scan_run(scan_run_id, "failed", error_msg)
            return error_msg

        finally:
            # Always reset tool's current scan run
            if tool_name in self.tools_map:
                self.tools_map[tool_name]._current_scan_run = None

    def _record_denied(
        self, tool_name: str, target: str, args: dict, message: str
    ) -> None:
        """Record a denied tool execution in findings DB."""
        if not self._findings_store:
            return
        try:
            run_id = self._findings_store.start_scan_run(
                session_id=self.session_id,
                tool_name=tool_name,
                target=target,
                args=args,
            )
            if run_id:
                self._findings_store.complete_scan_run(
                    run_id, status=ScanStatus.DENIED.value, raw_output=message
                )
        except Exception as e:
            logger.warning(f"Failed to record denied scan: {e}")

    def _start_scan_run(
        self, tool_name: str, target: Optional[str], args: dict
    ) -> Optional[str]:
        """Start a scan run in findings DB. Returns run ID or None."""
        if not self._findings_store:
            return None
        try:
            return self._findings_store.start_scan_run(
                session_id=self.session_id,
                tool_name=tool_name,
                target=target or "unknown",
                args=args,
            )
        except Exception as e:
            logger.warning(f"Failed to start scan run: {e}")
            return None

    def _complete_scan_run(
        self,
        scan_run_id: Optional[str],
        status: str,
        raw_output: Optional[str] = None,
    ) -> None:
        """Complete a scan run in findings DB."""
        if not self._findings_store or not scan_run_id:
            return
        try:
            self._findings_store.complete_scan_run(
                scan_run_id, status=status, raw_output=raw_output
            )
        except Exception as e:
            logger.warning(f"Failed to complete scan run: {e}")

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
            if hasattr(response, "usage") and response.usage:
                self.last_usage = response.usage
                self.last_prompt_tokens = response.usage.prompt_tokens
                self.total_tokens += response.usage.total_tokens

            # Keine Tool-Calls? → Fertig
            if not message.tool_calls:
                # Assistant-Antwort zur Session hinzufügen
                self.messages.append({"role": "assistant", "content": message.content})
                return message.content

            # Tool-Calls vorhanden - Message zur Session hinzufügen
            self.messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in message.tool_calls
                    ],
                }
            )

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                if self.verbose:
                    print(f"  Tool: {tool_name}({tool_args})")

                # Execute tool with auth, scope, and findings integration
                result = self._execute_tool(tool_name, tool_args)

                if self.verbose:
                    print(f"  Result: {result[:100]}...")

                # Tool-Result zur Session hinzufügen
                self.messages.append(
                    {"role": "tool", "tool_call_id": tool_call.id, "content": result}
                )

        return "Error: Max iterations reached"
