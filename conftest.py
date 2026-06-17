"""Shared pytest configuration and fixtures for all Airplast tests."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Ensure tests can load integrations from local custom_components/."""
    yield
