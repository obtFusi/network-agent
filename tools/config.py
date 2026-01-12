"""Centralized config loading for scan tools - v5.9 SSOT with State Normalization."""

import ipaddress
import os
from pathlib import Path
from typing import List, Optional
import yaml


def _get_config_path() -> Path:
    """Get config path: ENV override or relative to project root."""
    # v5.4: ENV-Override mit expanduser() for ~/config.yaml support
    if env_path := os.environ.get("NETWORK_AGENT_CONFIG"):
        return Path(env_path).expanduser().resolve()
    # v5.3: Relative to this module (not CWD!) - tools/config.py -> config/settings.yaml
    return Path(__file__).resolve().parents[1] / "config" / "settings.yaml"


def _validate_exclude_entry(entry: str) -> bool:
    """v5.5: Validate that entry is valid IPv4 IP or CIDR. Fail-Closed!

    IPv6 entries are rejected because scan tools only support IPv4.
    """
    try:
        net = ipaddress.ip_network(entry, strict=False)
        return net.version == 4  # v5.5: IPv4 only!
    except ValueError:
        pass
    try:
        ip = ipaddress.ip_address(entry)
        return ip.version == 4  # v5.5: IPv4 only!
    except ValueError:
        pass
    return False


class ScanConfig:
    """Lazy-loaded scan configuration from settings.yaml.

    v5.3: Does NOT crash on __init__ - errors are cached and surfaced in execute().
    v5.4: Type-Guards + Fail-Closed Exclude-Liste validation.
    v5.9: Config state normalization - scan dict is written back after validation.
    """

    def __init__(self):
        self._config: Optional[dict] = None
        self._error: Optional[str] = None
        self._load_attempted: bool = False

    def _ensure_loaded(self) -> None:
        """Lazy load config on first access."""
        if self._load_attempted:
            return
        self._load_attempted = True
        config_path = _get_config_path()
        if not config_path.exists():
            self._error = f"config not found: {config_path}"
            return
        try:
            self._config = yaml.safe_load(config_path.read_text()) or {}
        except yaml.YAMLError as e:
            self._error = f"invalid config YAML: {e}"
            return

        # v5.8: Validate scan is a dict (not list/string)
        # v5.9: scan: null/~ is now a config_error (not silently converted to {})
        scan = self._config.get("scan")
        if scan is None:
            # v5.9: Explicit null is config_error - user should omit key or use {}
            self._error = (
                "invalid config: scan is null/missing, use 'scan: {}' or omit entirely"
            )
            return
        if not isinstance(scan, dict):
            self._error = (
                f"invalid config: scan must be a mapping, got {type(scan).__name__}"
            )
            return

        # v5.4: Validate exclude_ips entries (Fail-Closed!)
        exclude_list = scan.get("exclude_ips", [])
        if not isinstance(exclude_list, list):
            self._error = "invalid config: scan.exclude_ips must be a list"
            return
        # v5.9: Normalize exclude_ips when loading (not in property)
        normalized_exclude = []
        for entry in exclude_list:
            if not isinstance(entry, str):
                self._error = f"invalid exclude entry: {entry!r} (must be string)"
                return
            # v5.7: Strip whitespace before validation (tolerant parsing)
            entry_stripped = entry.strip()
            if not entry_stripped or not _validate_exclude_entry(entry_stripped):
                self._error = f"invalid exclude entry: {entry!r} (must be IP or CIDR)"
                return
            normalized_exclude.append(entry_stripped)
        # v5.9: Write normalized list back to config state
        scan["exclude_ips"] = normalized_exclude

        # v5.6: Type-Guards for numeric values (bool is subclass of int, must exclude!)
        for key in ["max_hosts_discovery", "max_hosts_portscan", "timeout"]:
            val = scan.get(key)
            # v5.6: type(val) is int excludes bool! isinstance(val, int) is True for bool.
            if val is not None and type(val) is not int:
                self._error = f"invalid config: scan.{key} must be integer, got {type(val).__name__}"
                return
            # v5.5: Range validation - must be positive
            if val is not None and val < 1:
                self._error = f"invalid config: scan.{key} must be >= 1, got {val}"
                return
        # v5.7: tcp_ports validation - empty/whitespace-only string is invalid
        tcp_ports = scan.get("tcp_ports")
        if tcp_ports is not None:
            if not isinstance(tcp_ports, str):
                self._error = f"invalid config: scan.tcp_ports must be string, got {type(tcp_ports).__name__}"
                return
            # v5.7: Both empty string and whitespace-only are invalid
            if tcp_ports.strip() == "":
                self._error = (
                    "invalid config: scan.tcp_ports cannot be empty or whitespace-only"
                )
                return

        # v5.9: Write validated scan dict back to config (ensures Properties don't access raw state)
        self._config["scan"] = scan

    def get_error(self) -> Optional[str]:
        """Returns error message if config loading failed. Used by Tools."""
        self._ensure_loaded()
        return self._error

    @property
    def exclude_ips(self) -> List[str]:
        """Get exclude list. Returns empty list if config invalid (safe for listing).

        v5.9: Already normalized when loading - no strip() needed here.
        """
        self._ensure_loaded()
        if self._error:
            return []  # v5.3: Safe default for --list-tools
        # v5.9: Read directly from normalized config state
        return self._config["scan"].get("exclude_ips", [])

    @property
    def max_hosts_discovery(self) -> int:
        """Max hosts for ping_sweep (default: 65536 = /16). v5.3: Split!"""
        self._ensure_loaded()
        if self._error:
            return 65536  # Safe default
        # v5.9: scan is guaranteed to be a dict after _ensure_loaded
        return self._config["scan"].get("max_hosts_discovery", 65536)

    @property
    def max_hosts_portscan(self) -> int:
        """Max hosts for port_scan/service_detect (default: 256 = /24). v5.3: Split!"""
        self._ensure_loaded()
        if self._error:
            return 256  # Safe default
        return self._config["scan"].get("max_hosts_portscan", 256)

    @property
    def timeout(self) -> int:
        """Default timeout in seconds (default: 120). v5.3: Actually used!"""
        self._ensure_loaded()
        if self._error:
            return 120
        return self._config["scan"].get("timeout", 120)

    @property
    def tcp_ports(self) -> Optional[str]:
        """Default TCP ports for port_scan (fallback). v5.3: Actually used!"""
        self._ensure_loaded()
        if self._error:
            return None
        return self._config["scan"].get("tcp_ports")


# Singleton instance
_config: Optional[ScanConfig] = None


def get_scan_config() -> ScanConfig:
    """Get singleton config instance. v5.3: Never crashes, use get_error() to check."""
    global _config
    if _config is None:
        _config = ScanConfig()
    return _config


def reset_scan_config() -> None:
    """Reset singleton for testing. v5.3: Test helper."""
    global _config
    _config = None
