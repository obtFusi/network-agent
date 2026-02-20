"""Scope enforcement for target validation.

Parses scope files containing allowed CIDR ranges and hostnames.
When active, ALL tool targets are validated against the allowlist.
"""

import ipaddress
import logging
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)


class ScopeConfig:
    """Manages target scope validation.

    When a scope file is loaded, only targets within the defined
    CIDRs/hostnames are allowed. Without a scope file, the existing
    resolve_and_validate() private-IP-only behavior applies.
    """

    def __init__(self):
        self._networks: List[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        self._hosts: List[str] = []
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        """Whether a scope file has been loaded."""
        return self._loaded

    def load(self, file_path: str) -> None:
        """Load scope file. One CIDR or hostname per line, # comments."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Scope file not found: {file_path}")

        self._networks = []
        self._hosts = []

        for line in path.read_text().splitlines():
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Try as CIDR network
            try:
                network = ipaddress.ip_network(line, strict=False)
                self._networks.append(network)
                continue
            except ValueError:
                pass

            # Try as single IP
            try:
                addr = ipaddress.ip_address(line)
                self._networks.append(
                    ipaddress.ip_network(f"{addr}/{addr.max_prefixlen}")
                )
                continue
            except ValueError:
                pass

            # Treat as hostname
            self._hosts.append(line.lower())

        self._loaded = True
        logger.info(
            f"Scope loaded: {len(self._networks)} networks, {len(self._hosts)} hosts"
        )

    def is_in_scope(self, target: str) -> Tuple[bool, str]:
        """Check if target is within scope.

        Args:
            target: IP address, CIDR, or hostname

        Returns:
            (in_scope, denial_message)
        """
        if not self._loaded:
            return (True, "")

        target = target.strip()

        # Try as IP address
        try:
            addr = ipaddress.ip_address(target)
            for network in self._networks:
                if addr in network:
                    return (True, "")
            return (
                False,
                f"Target '{target}' is outside defined scope. "
                "Check --scope-file for allowed targets.",
            )
        except ValueError:
            pass

        # Try as CIDR network
        try:
            net = ipaddress.ip_network(target, strict=False)
            for allowed in self._networks:
                # Check if the target network is a subset of an allowed network
                if net.subnet_of(allowed):
                    return (True, "")
            return (
                False,
                f"Network '{target}' is outside defined scope.",
            )
        except ValueError:
            pass

        # Treat as hostname
        if target.lower() in self._hosts:
            return (True, "")

        return (
            False,
            f"Target '{target}' is not in scope. "
            "Check --scope-file for allowed targets.",
        )
