"""Tests for ScopeConfig: parsing, IP/CIDR/hostname validation, edge cases."""

from pathlib import Path

import pytest

from tools.scope import ScopeConfig


@pytest.fixture
def scope():
    """Fresh ScopeConfig instance."""
    return ScopeConfig()


@pytest.fixture
def scope_file(tmp_path):
    """Create a scope file helper."""

    def _create(content: str) -> str:
        path = tmp_path / "scope.txt"
        path.write_text(content)
        return str(path)

    return _create


class TestScopeConfigInit:
    def test_not_loaded_by_default(self, scope):
        assert not scope.is_loaded

    def test_allows_everything_when_not_loaded(self, scope):
        in_scope, msg = scope.is_in_scope("10.0.0.1")
        assert in_scope
        assert msg == ""

    def test_allows_any_target_when_not_loaded(self, scope):
        in_scope, _ = scope.is_in_scope("evil.example.com")
        assert in_scope


class TestScopeFileLoading:
    def test_load_sets_loaded(self, scope, scope_file):
        path = scope_file("10.0.0.0/24\n")
        scope.load(path)
        assert scope.is_loaded

    def test_load_nonexistent_file_raises(self, scope):
        with pytest.raises(FileNotFoundError):
            scope.load("/nonexistent/scope.txt")

    def test_load_cidr(self, scope, scope_file):
        path = scope_file("192.168.1.0/24\n")
        scope.load(path)
        in_scope, _ = scope.is_in_scope("192.168.1.50")
        assert in_scope

    def test_load_single_ip(self, scope, scope_file):
        path = scope_file("10.0.0.5\n")
        scope.load(path)
        in_scope, _ = scope.is_in_scope("10.0.0.5")
        assert in_scope

    def test_load_hostname(self, scope, scope_file):
        path = scope_file("dc01.corp.local\n")
        scope.load(path)
        in_scope, _ = scope.is_in_scope("dc01.corp.local")
        assert in_scope

    def test_skip_empty_lines(self, scope, scope_file):
        path = scope_file("\n\n10.0.0.0/24\n\n")
        scope.load(path)
        in_scope, _ = scope.is_in_scope("10.0.0.1")
        assert in_scope

    def test_skip_comments(self, scope, scope_file):
        path = scope_file("# Lab network\n10.0.0.0/24\n# Another comment\n")
        scope.load(path)
        in_scope, _ = scope.is_in_scope("10.0.0.1")
        assert in_scope

    def test_load_mixed_entries(self, scope, scope_file):
        content = """# Scope file
10.0.0.0/24
192.168.1.100
dc01.corp.local
# End
"""
        path = scope_file(content)
        scope.load(path)

        assert scope.is_in_scope("10.0.0.50")[0]
        assert scope.is_in_scope("192.168.1.100")[0]
        assert scope.is_in_scope("dc01.corp.local")[0]


class TestIPValidation:
    def test_ip_in_cidr(self, scope, scope_file):
        path = scope_file("172.16.0.0/16\n")
        scope.load(path)
        assert scope.is_in_scope("172.16.5.10")[0]

    def test_ip_not_in_cidr(self, scope, scope_file):
        path = scope_file("172.16.0.0/16\n")
        scope.load(path)
        in_scope, msg = scope.is_in_scope("10.0.0.1")
        assert not in_scope
        assert "outside" in msg.lower() or "not in scope" in msg.lower()

    def test_exact_ip_match(self, scope, scope_file):
        path = scope_file("10.0.0.42\n")
        scope.load(path)
        assert scope.is_in_scope("10.0.0.42")[0]
        assert not scope.is_in_scope("10.0.0.43")[0]

    def test_multiple_cidrs(self, scope, scope_file):
        path = scope_file("10.0.0.0/24\n192.168.1.0/24\n")
        scope.load(path)
        assert scope.is_in_scope("10.0.0.100")[0]
        assert scope.is_in_scope("192.168.1.50")[0]
        assert not scope.is_in_scope("172.16.0.1")[0]

    def test_cidr_boundary(self, scope, scope_file):
        path = scope_file("10.0.0.0/30\n")
        scope.load(path)
        # /30 = 10.0.0.0 - 10.0.0.3
        assert scope.is_in_scope("10.0.0.0")[0]
        assert scope.is_in_scope("10.0.0.3")[0]
        assert not scope.is_in_scope("10.0.0.4")[0]


class TestCIDRTargetValidation:
    def test_target_cidr_subset_of_scope(self, scope, scope_file):
        path = scope_file("10.0.0.0/16\n")
        scope.load(path)
        # /24 is a subset of /16
        assert scope.is_in_scope("10.0.1.0/24")[0]

    def test_target_cidr_not_subset(self, scope, scope_file):
        path = scope_file("10.0.0.0/24\n")
        scope.load(path)
        # /16 is NOT a subset of /24
        in_scope, msg = scope.is_in_scope("10.0.0.0/16")
        assert not in_scope
        assert "outside" in msg.lower()


class TestHostnameValidation:
    def test_hostname_in_scope(self, scope, scope_file):
        path = scope_file("server1.lab.local\n")
        scope.load(path)
        assert scope.is_in_scope("server1.lab.local")[0]

    def test_hostname_not_in_scope(self, scope, scope_file):
        path = scope_file("server1.lab.local\n")
        scope.load(path)
        in_scope, msg = scope.is_in_scope("server2.lab.local")
        assert not in_scope
        assert "not in scope" in msg.lower()

    def test_hostname_case_insensitive(self, scope, scope_file):
        path = scope_file("DC01.Corp.Local\n")
        scope.load(path)
        assert scope.is_in_scope("dc01.corp.local")[0]
        assert scope.is_in_scope("DC01.CORP.LOCAL")[0]

    def test_hostname_with_whitespace(self, scope, scope_file):
        path = scope_file("  server1.local  \n")
        scope.load(path)
        assert scope.is_in_scope("server1.local")[0]


class TestEdgeCases:
    def test_target_with_whitespace_trimmed(self, scope, scope_file):
        path = scope_file("10.0.0.0/24\n")
        scope.load(path)
        assert scope.is_in_scope("  10.0.0.1  ")[0]

    def test_reload_replaces_previous(self, scope, scope_file):
        path1 = scope_file("10.0.0.0/24\n")
        scope.load(path1)
        assert scope.is_in_scope("10.0.0.1")[0]

        # Reload with different scope
        path2 = Path(path1).parent / "scope2.txt"
        path2.write_text("192.168.1.0/24\n")
        scope.load(str(path2))

        assert not scope.is_in_scope("10.0.0.1")[0]
        assert scope.is_in_scope("192.168.1.1")[0]

    def test_ipv6_cidr(self, scope, scope_file):
        path = scope_file("fd00::/64\n")
        scope.load(path)
        assert scope.is_in_scope("fd00::1")[0]
        assert not scope.is_in_scope("fd01::1")[0]

    def test_empty_scope_file_blocks_all(self, scope, scope_file):
        path = scope_file("# Only comments\n\n")
        scope.load(path)
        # Loaded but empty = blocks everything
        assert scope.is_loaded
        in_scope, _ = scope.is_in_scope("10.0.0.1")
        assert not in_scope
