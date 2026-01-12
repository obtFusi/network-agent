"""
Tests for tools/config.py

Tests config loading, validation, and type guards.
"""

from unittest.mock import patch
from tools.config import get_scan_config, reset_scan_config


class TestScanConfig:
    """Tests for ScanConfig class."""

    def test_invalid_exclude_entry_sets_error(self, tmp_path):
        """v5.4: Fail-Closed - invalid exclude entry -> config_error."""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("scan:\n  exclude_ips:\n    - 'not-a-cidr'\n")
        with patch.dict("os.environ", {"NETWORK_AGENT_CONFIG": str(config_file)}):
            reset_scan_config()
            config = get_scan_config()
            assert config.get_error() is not None
            assert "invalid exclude entry" in config.get_error()

    def test_invalid_timeout_type_sets_error(self, tmp_path):
        """v5.4: Type-Guard - timeout: 'abc' -> config_error."""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("scan:\n  timeout: 'abc'\n")
        with patch.dict("os.environ", {"NETWORK_AGENT_CONFIG": str(config_file)}):
            reset_scan_config()
            config = get_scan_config()
            assert config.get_error() is not None
            assert "timeout" in config.get_error()
            assert "integer" in config.get_error()

    def test_valid_config_no_error(self, tmp_path):
        """v5.4: Valid config -> no error."""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text(
            "scan:\n  exclude_ips:\n    - '192.168.1.0/24'\n  timeout: 180\n"
        )
        with patch.dict("os.environ", {"NETWORK_AGENT_CONFIG": str(config_file)}):
            reset_scan_config()
            config = get_scan_config()
            assert config.get_error() is None
            assert config.timeout == 180

    def test_expanduser_in_env_path(self, tmp_path, monkeypatch):
        """v5.5: ENV path with ~ is expanded."""
        # Create config in tmp_path
        config_file = tmp_path / "test-settings.yaml"
        config_file.write_text("scan:\n  timeout: 200\n")

        # v5.8: Set HOME to tmp_path so ~ expands correctly
        monkeypatch.setenv("HOME", str(tmp_path))

        # Use ~ in ENV path
        with patch.dict("os.environ", {"NETWORK_AGENT_CONFIG": "~/test-settings.yaml"}):
            reset_scan_config()
            config = get_scan_config()
            assert config.get_error() is None
            assert config.timeout == 200

    # v5.5: IPv6 exclude entry rejected
    def test_ipv6_exclude_entry_rejected(self, tmp_path):
        """v5.5: IPv6 exclude entries are rejected (scan tools only support IPv4)."""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("scan:\n  exclude_ips:\n    - '::1'\n")
        with patch.dict("os.environ", {"NETWORK_AGENT_CONFIG": str(config_file)}):
            reset_scan_config()
            config = get_scan_config()
            assert config.get_error() is not None
            assert "invalid exclude entry" in config.get_error()

    def test_ipv6_cidr_exclude_rejected(self, tmp_path):
        """v5.5: IPv6 CIDR in exclude list rejected."""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("scan:\n  exclude_ips:\n    - 'fe80::/10'\n")
        with patch.dict("os.environ", {"NETWORK_AGENT_CONFIG": str(config_file)}):
            reset_scan_config()
            config = get_scan_config()
            assert config.get_error() is not None
            assert "invalid exclude entry" in config.get_error()

    # v5.5: Range validation
    def test_timeout_zero_rejected(self, tmp_path):
        """v5.5: timeout: 0 -> config_error."""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("scan:\n  timeout: 0\n")
        with patch.dict("os.environ", {"NETWORK_AGENT_CONFIG": str(config_file)}):
            reset_scan_config()
            config = get_scan_config()
            assert config.get_error() is not None
            assert "must be >= 1" in config.get_error()

    def test_max_hosts_negative_rejected(self, tmp_path):
        """v5.5: max_hosts_portscan: -1 -> config_error."""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("scan:\n  max_hosts_portscan: -1\n")
        with patch.dict("os.environ", {"NETWORK_AGENT_CONFIG": str(config_file)}):
            reset_scan_config()
            config = get_scan_config()
            assert config.get_error() is not None
            assert "must be >= 1" in config.get_error()

    # v5.6: Bool-Type-Guard Tests
    def test_bool_timeout_rejected(self, tmp_path):
        """v5.6: timeout: true -> config_error (bool is subclass of int!)."""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("scan:\n  timeout: true\n")
        with patch.dict("os.environ", {"NETWORK_AGENT_CONFIG": str(config_file)}):
            reset_scan_config()
            config = get_scan_config()
            assert config.get_error() is not None
            assert "integer" in config.get_error()

    def test_bool_max_hosts_rejected(self, tmp_path):
        """v5.6: max_hosts_portscan: false -> config_error."""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("scan:\n  max_hosts_portscan: false\n")
        with patch.dict("os.environ", {"NETWORK_AGENT_CONFIG": str(config_file)}):
            reset_scan_config()
            config = get_scan_config()
            assert config.get_error() is not None
            assert "integer" in config.get_error()

    # v5.6: Empty tcp_ports Test
    def test_empty_tcp_ports_rejected(self, tmp_path):
        """v5.6: tcp_ports: '' -> config_error (empty string is invalid)."""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("scan:\n  tcp_ports: ''\n")
        with patch.dict("os.environ", {"NETWORK_AGENT_CONFIG": str(config_file)}):
            reset_scan_config()
            config = get_scan_config()
            assert config.get_error() is not None
            assert "empty" in config.get_error().lower()

    # v5.7: Whitespace-only tcp_ports Test
    def test_whitespace_only_tcp_ports_rejected(self, tmp_path):
        """v5.7: tcp_ports: '   ' -> config_error (whitespace-only is invalid)."""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("scan:\n  tcp_ports: '   '\n")
        with patch.dict("os.environ", {"NETWORK_AGENT_CONFIG": str(config_file)}):
            reset_scan_config()
            config = get_scan_config()
            assert config.get_error() is not None
            assert (
                "empty" in config.get_error().lower()
                or "whitespace" in config.get_error().lower()
            )

    # v5.7: exclude_ips with whitespace (tolerant parsing)
    def test_exclude_ips_with_whitespace_valid(self, tmp_path):
        """v5.7: exclude_ips with leading/trailing whitespace is accepted after strip."""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("scan:\n  exclude_ips:\n    - '  192.168.1.0/24  '\n")
        with patch.dict("os.environ", {"NETWORK_AGENT_CONFIG": str(config_file)}):
            reset_scan_config()
            config = get_scan_config()
            # Should be valid after stripping whitespace
            assert config.get_error() is None

    # v5.8: scan-Typ-Check
    def test_scan_not_dict_rejected(self, tmp_path):
        """v5.8: scan: 'not-a-dict' -> config_error."""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("scan: 'this is a string'\n")
        with patch.dict("os.environ", {"NETWORK_AGENT_CONFIG": str(config_file)}):
            reset_scan_config()
            config = get_scan_config()
            assert config.get_error() is not None
            assert "mapping" in config.get_error()

    def test_scan_list_rejected(self, tmp_path):
        """v5.8: scan: [1, 2, 3] -> config_error."""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("scan:\n  - item1\n  - item2\n")
        with patch.dict("os.environ", {"NETWORK_AGENT_CONFIG": str(config_file)}):
            reset_scan_config()
            config = get_scan_config()
            assert config.get_error() is not None
            assert "mapping" in config.get_error()

    # v5.8: exclude_ips returns normalized
    def test_exclude_ips_returned_normalized(self, tmp_path):
        """v5.8: exclude_ips property returns stripped entries."""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text(
            "scan:\n  exclude_ips:\n    - '  192.168.1.0/24  '\n    - ' 10.0.0.0/8 '\n"
        )
        with patch.dict("os.environ", {"NETWORK_AGENT_CONFIG": str(config_file)}):
            reset_scan_config()
            config = get_scan_config()
            assert config.get_error() is None
            # v5.8: Property must return normalized (stripped) values
            assert config.exclude_ips == ["192.168.1.0/24", "10.0.0.0/8"]

    # v5.9: scan: null rejected
    def test_scan_null_rejected(self, tmp_path):
        """v5.9: scan: null/~ -> config_error (not silently converted to {})."""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("scan: ~\n")
        with patch.dict("os.environ", {"NETWORK_AGENT_CONFIG": str(config_file)}):
            reset_scan_config()
            config = get_scan_config()
            assert config.get_error() is not None
            assert (
                "null" in config.get_error().lower()
                or "missing" in config.get_error().lower()
            )

    def test_scan_missing_rejected(self, tmp_path):
        """v5.9: Missing scan key -> config_error."""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("llm:\n  provider:\n    model: 'test'\n")
        with patch.dict("os.environ", {"NETWORK_AGENT_CONFIG": str(config_file)}):
            reset_scan_config()
            config = get_scan_config()
            assert config.get_error() is not None
            assert (
                "null" in config.get_error().lower()
                or "missing" in config.get_error().lower()
            )

    def test_default_values_used(self, tmp_path):
        """Config uses defaults when values not specified."""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("scan:\n  timeout: 90\n")
        with patch.dict("os.environ", {"NETWORK_AGENT_CONFIG": str(config_file)}):
            reset_scan_config()
            config = get_scan_config()
            assert config.get_error() is None
            assert config.timeout == 90
            # Defaults
            assert config.max_hosts_discovery == 65536
            assert config.max_hosts_portscan == 256
            assert config.exclude_ips == []

    def test_config_not_found_error(self, tmp_path):
        """Missing config file sets error."""
        with patch.dict(
            "os.environ", {"NETWORK_AGENT_CONFIG": str(tmp_path / "nonexistent.yaml")}
        ):
            reset_scan_config()
            config = get_scan_config()
            assert config.get_error() is not None
            assert "not found" in config.get_error()
            # Should still return safe defaults
            assert config.exclude_ips == []
            assert config.max_hosts_discovery == 65536
