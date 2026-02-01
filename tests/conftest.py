"""
Root conftest.py for assistant-skills-lib tests.

Provides pytest hooks and shared fixtures for all tests.

Hooks:
- pytest_addoption: Adds --live CLI flag for running live API tests
- pytest_configure: Registers markers programmatically
- pytest_collection_modifyitems: Skips live tests unless --live flag is provided

Fixtures:
- mock_config: Sample configuration dictionary
"""

import pytest


# =============================================================================
# Pytest Hooks
# =============================================================================


def pytest_addoption(parser):
    """Add custom CLI options for pytest."""
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="Run live API tests (requires credentials)",
    )


def pytest_configure(config):
    """Register custom markers."""
    # Core markers
    config.addinivalue_line("markers", "unit: Unit tests (fast, no external calls)")
    config.addinivalue_line(
        "markers", "integration: Integration tests (may require credentials)"
    )
    config.addinivalue_line("markers", "slow: Slow-running tests")
    config.addinivalue_line("markers", "live: Tests requiring live API credentials")
    config.addinivalue_line("markers", "destructive: Tests that modify or delete data")

    # Component markers
    config.addinivalue_line("markers", "cache: Cache tests")
    config.addinivalue_line("markers", "config: Configuration tests")
    config.addinivalue_line("markers", "credentials: Credential manager tests")
    config.addinivalue_line("markers", "formatters: Output formatter tests")
    config.addinivalue_line("markers", "validators: Input validator tests")
    config.addinivalue_line("markers", "errors: Error handler tests")
    config.addinivalue_line("markers", "templates: Template engine tests")
    config.addinivalue_line("markers", "batch: Batch processor tests")


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on CLI flags."""
    if not config.getoption("--live"):
        skip_live = pytest.mark.skip(reason="need --live option to run")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip_live)


# =============================================================================
# Shared Fixtures
# =============================================================================


@pytest.fixture
def mock_config():
    """Sample configuration dictionary for testing."""
    return {
        "site_url": "https://test.example.com",
        "email": "test@example.com",
        "api_token": "test-token",
        "default_project": "TEST",
        "page_size": 50,
    }


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Temporary directory for cache testing."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir
