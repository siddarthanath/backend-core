"""Skip all integration tests unless INTEGRATION_TESTS=1 is set."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import os

# Third Party
import pytest

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


def pytest_collection_modifyitems(items):
    if os.getenv("INTEGRATION_TESTS") != "1":
        skip = pytest.mark.skip(reason="Integration tests require INTEGRATION_TESTS=1 and a test database")
        for item in items:
            if "integration" in item.nodeid:
                item.add_marker(skip)
