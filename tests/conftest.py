"""
Shared pytest fixtures for network-agent tests.
"""

import pytest
from pathlib import Path
from tools.config import reset_scan_config


@pytest.fixture
def fixtures_path() -> Path:
    """Path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def nmap_outputs_path(fixtures_path) -> Path:
    """Path to nmap output fixtures."""
    return fixtures_path / "nmap_outputs"


@pytest.fixture(autouse=True)
def reset_config_singleton():
    """v5.4: Reset config singleton before each test to avoid test pollution."""
    reset_scan_config()
    yield
    reset_scan_config()
