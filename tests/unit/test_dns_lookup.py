"""Tests for tools/network/dns_lookup.py"""

from unittest.mock import patch, MagicMock
from tools.network.dns_lookup import DNSLookupTool


class TestDNSLookupTool:
    def setup_method(self):
        self.tool = DNSLookupTool()

    def test_name(self):
        assert self.tool.name == "dns_lookup"

    def test_description_mentions_dns(self):
        assert "DNS" in self.tool.description

    def test_parameters_has_target(self):
        assert "target" in self.tool.parameters["properties"]
        assert "target" in self.tool.parameters["required"]

    def test_parameters_has_record_type(self):
        assert "record_type" in self.tool.parameters["properties"]

    @patch("tools.network.dns_lookup.dns.resolver.Resolver")
    def test_a_record_lookup(self, mock_resolver_class):
        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver
        mock_answer = MagicMock()
        mock_answer.__str__ = lambda s: "93.184.216.34"
        mock_resolver.resolve.return_value = [mock_answer]

        result = self.tool.execute("example.com", "A")
        assert "93.184.216.34" in result
        assert "DNS Lookup" in result

    def test_empty_target(self):
        result = self.tool.execute("")
        assert "Error" in result
        assert "No target" in result

    def test_whitespace_only_target(self):
        result = self.tool.execute("   ")
        assert "Error" in result

    @patch("tools.network.dns_lookup.dns.resolver.Resolver")
    def test_auto_detects_ptr_for_ip(self, mock_resolver_class):
        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver
        mock_answer = MagicMock()
        mock_answer.__str__ = lambda s: "dns.google."
        mock_resolver.resolve.return_value = [mock_answer]

        result = self.tool.execute("8.8.8.8", "auto")
        # PTR lookup should be used for IP
        assert "PTR" in result or "dns.google" in result

    def test_ptr_guard_rejects_hostname_with_ptr(self):
        """PTR lookup requires IP, not hostname."""
        result = self.tool.execute("example.com", "PTR")
        assert "Error" in result
        assert "IP address" in result

    def test_record_type_case_insensitive(self):
        """Lowercase record types should work (LLMs send lowercase)."""
        with patch("tools.network.dns_lookup.dns.resolver.Resolver") as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            mock_answer = MagicMock()
            mock_answer.__str__ = lambda s: "10.0.0.1"
            mock_instance.resolve.return_value = [mock_answer]

            result = self.tool.execute("example.local", "a")  # lowercase!
            assert "Invalid record type" not in result

    def test_trailing_dot_normalized(self):
        """FQDN trailing dot should be normalized."""
        with patch("tools.network.dns_lookup.dns.resolver.Resolver") as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            mock_answer = MagicMock()
            mock_answer.__str__ = lambda s: "10.0.0.1"
            mock_instance.resolve.return_value = [mock_answer]

            result = self.tool.execute("example.local.", "A")  # with trailing dot
            mock_instance.resolve.assert_called()
            # Should not fail
            assert "Error" not in result or "Invalid" not in result

    def test_invalid_record_type_rejected(self):
        """Invalid record type should return error."""
        result = self.tool.execute("example.com", "INVALID")
        assert "Error" in result
        assert "Invalid record type" in result

    @patch("tools.network.dns_lookup.dns.resolver.Resolver")
    def test_nxdomain_handled(self, mock_resolver_class):
        """NXDOMAIN should return friendly error."""
        import dns.resolver

        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver
        mock_resolver.resolve.side_effect = dns.resolver.NXDOMAIN()

        result = self.tool.execute("nonexistent.invalid", "A")
        assert "Error" in result
        assert "not found" in result

    @patch("tools.network.dns_lookup.dns.resolver.Resolver")
    def test_timeout_handled(self, mock_resolver_class):
        """Timeout should return friendly error."""
        import dns.resolver

        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver
        mock_resolver.resolve.side_effect = dns.resolver.Timeout()

        result = self.tool.execute("slow.example.com", "A")
        assert "Error" in result
        assert "timed out" in result


class TestDNSLookupTypeGuards:
    """Type guards for LLM input validation."""

    def setup_method(self):
        self.tool = DNSLookupTool()

    def test_target_not_string_rejected(self):
        result = self.tool.execute(target=123)
        assert "Error" in result
        assert "target must be string" in result

    def test_record_type_not_string_rejected(self):
        result = self.tool.execute(target="example.com", record_type=123)
        assert "Error" in result
        assert "record_type must be string" in result

    def test_timeout_not_int_rejected(self):
        result = self.tool.execute(target="example.com", timeout="10")
        assert "Error" in result
        assert "timeout must be integer" in result

    def test_timeout_bool_rejected(self):
        """Bool is int subclass, but should be rejected."""
        result = self.tool.execute(target="example.com", timeout=True)
        assert "Error" in result
        assert "timeout must be integer" in result

    def test_timeout_zero_rejected(self):
        """timeout=0 should be rejected (>= 1 required)."""
        result = self.tool.execute(target="example.com", timeout=0)
        assert "Error" in result
        assert ">= 1" in result

    def test_timeout_negative_rejected(self):
        """Negative timeout should be rejected."""
        result = self.tool.execute(target="example.com", timeout=-5)
        assert "Error" in result
