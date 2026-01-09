"""
Shared pytest fixtures for network-agent tests.
"""

import pytest
from pathlib import Path


@pytest.fixture
def fixtures_path() -> Path:
    """Path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def nmap_outputs_path(fixtures_path) -> Path:
    """Path to nmap output fixtures."""
    return fixtures_path / "nmap_outputs"
