"""3-Tier Authorization System for attack simulation tools.

Levels:
    - passive: Read-only tools (default, no flag required)
    - active: Network-active tools (requires --i-have-written-authorization)
    - destructive: RCE/persistence tools (requires flag + per-tool CLI confirmation)
"""

import time
from enum import Enum
from typing import Dict, Tuple


class AuthorizationLevel(str, Enum):
    """Authorization levels ordered by severity."""

    PASSIVE = "passive"
    ACTIVE = "active"
    DESTRUCTIVE = "destructive"

    @property
    def numeric(self) -> int:
        """Numeric value for comparison."""
        return {"passive": 0, "active": 1, "destructive": 2}[self.value]

    def allows(self, required: "AuthorizationLevel") -> bool:
        """Check if this level allows the required level."""
        return self.numeric >= required.numeric


class AuthorizationConfig:
    """Manages authorization state for the current session.

    The authorization level is set once at startup via CLI flag or config.
    Destructive tools additionally require per-tool confirmation via CLI input().
    Confirmation is keyed on (tool_name, target) and expires after TTL.
    """

    DEFAULT_TTL_SECONDS = 3600  # 1 hour

    def __init__(self, level: str = "passive"):
        try:
            self._level = AuthorizationLevel(level)
        except ValueError:
            # Fail-closed: invalid level defaults to passive
            self._level = AuthorizationLevel.PASSIVE

        # Keyed on (tool_name, target) -> timestamp
        self._destructive_confirmed: Dict[Tuple[str, str], bool] = {}
        self._destructive_confirmed_at: Dict[Tuple[str, str], float] = {}

    @property
    def level(self) -> AuthorizationLevel:
        """Current authorization level."""
        return self._level

    def check(self, tool_name: str, required: str) -> tuple:
        """Check if the current authorization level allows execution.

        Args:
            tool_name: Name of the tool requesting authorization
            required: Required authorization level string

        Returns:
            (allowed: bool, denial_message: str)
        """
        try:
            required_level = AuthorizationLevel(required)
        except ValueError:
            # Fail-closed: unknown required level -> deny
            return (False, f"Unknown authorization level: {required}")

        if self._level.allows(required_level):
            return (True, "")

        if required_level == AuthorizationLevel.ACTIVE:
            return (
                False,
                f"Authorization denied for '{tool_name}': requires active authorization. "
                "Start with --i-have-written-authorization flag to enable active tools.",
            )
        elif required_level == AuthorizationLevel.DESTRUCTIVE:
            return (
                False,
                f"Authorization denied for '{tool_name}': requires destructive authorization. "
                "Start with --i-have-written-authorization flag and confirm each destructive action.",
            )

        return (
            False,
            f"Authorization denied for '{tool_name}': insufficient authorization level.",
        )

    def requires_confirmation(self, tool_name: str, target: str) -> bool:
        """Check if a destructive tool needs (re-)confirmation.

        Confirmation is keyed on (tool_name, target) - approval for tool A
        on target X does NOT authorize tool A on target Y.

        Returns:
            True if confirmation is needed (not confirmed or expired).
        """
        key = (tool_name, target)
        if key not in self._destructive_confirmed:
            return True
        if not self._destructive_confirmed[key]:
            return True
        return self.is_confirmation_expired(tool_name, target)

    def confirm_destructive(self, tool_name: str, target: str) -> None:
        """Record destructive tool confirmation.

        Called ONLY from CLI input(), NEVER from LLM.
        """
        key = (tool_name, target)
        self._destructive_confirmed[key] = True
        self._destructive_confirmed_at[key] = time.time()

    def is_confirmation_expired(
        self, tool_name: str, target: str, ttl_seconds: int = DEFAULT_TTL_SECONDS
    ) -> bool:
        """Check if a destructive confirmation has expired.

        Args:
            tool_name: Tool name
            target: Target host/network
            ttl_seconds: Time-to-live in seconds (default: 1 hour)

        Returns:
            True if expired or never confirmed.
        """
        key = (tool_name, target)
        if key not in self._destructive_confirmed_at:
            return True
        elapsed = time.time() - self._destructive_confirmed_at[key]
        return elapsed > ttl_seconds
