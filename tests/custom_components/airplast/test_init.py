"""Integration setup / teardown tests for the Airplast integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.airplast.client import AirplastRequestError
from custom_components.airplast.const import (
    DATA_CLIENT,
    DATA_COORDINATOR,
    DOMAIN,
)

from .conftest import (
    MOCK_TOKEN,
    MOCK_USERNAME,
    build_mock_ha_client,
    mock_config_entry,
)

# Re-export fixture so pytest can discover it in this module
from .conftest import mock_config_entry  # noqa: F811


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patch_coordinator(client=None):
    """Patch AirplastCoordinator so first refresh succeeds without HTTP calls."""
    if client is None:
        client = build_mock_ha_client()

    mock_coordinator = MagicMock()
    mock_coordinator.async_config_entry_first_refresh = AsyncMock()
    mock_coordinator.data = {
        42: {
            "devices": {},
            "house_info": None,
        }
    }
    mock_coordinator.last_update_success = True
    mock_coordinator.async_add_listener = MagicMock(return_value=lambda: None)

    return mock_coordinator


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------


async def test_setup_entry_stores_client_and_coordinator(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """async_setup_entry should populate hass.data with client and coordinator."""
    mock_config_entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.airplast.AirplastHAClient",
            return_value=build_mock_ha_client(),
        ),
        patch(
            "custom_components.airplast.AirplastCoordinator",
            return_value=_patch_coordinator(),
        ),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new=AsyncMock(),
        ),
    ):
        result = await hass.config_entries.async_setup(mock_config_entry.entry_id)

    assert result is True
    assert DOMAIN in hass.data
    entry_data = hass.data[DOMAIN][mock_config_entry.entry_id]
    assert DATA_CLIENT in entry_data
    assert DATA_COORDINATOR in entry_data


async def test_setup_entry_raises_not_ready_on_transport_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Backend transport failure marks entry as SETUP_RETRY."""

    mock_config_entry.add_to_hass(hass)

    coord = MagicMock()
    coord.async_config_entry_first_refresh = AsyncMock(
        side_effect=AirplastRequestError("connection refused")
    )
    coord.async_add_listener = MagicMock(return_value=lambda: None)

    with (
        patch("custom_components.airplast.AirplastHAClient", return_value=build_mock_ha_client()),
        patch("custom_components.airplast.AirplastCoordinator", return_value=coord),
    ):
        result = await hass.config_entries.async_setup(mock_config_entry.entry_id)

    assert result is False
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


# ---------------------------------------------------------------------------
# Unload
# ---------------------------------------------------------------------------


async def test_unload_entry_cleans_up(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """async_unload_entry removes hass.data entry."""
    mock_config_entry.add_to_hass(hass)

    mock_coord = _patch_coordinator()

    with (
        patch("custom_components.airplast.AirplastHAClient", return_value=build_mock_ha_client()),
        patch("custom_components.airplast.AirplastCoordinator", return_value=mock_coord),
        patch.object(hass.config_entries, "async_forward_entry_setups", new=AsyncMock()),
        patch.object(hass.config_entries, "async_unload_platforms", new=AsyncMock(return_value=True)),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        assert mock_config_entry.entry_id in hass.data.get(DOMAIN, {})

        result = await hass.config_entries.async_unload(mock_config_entry.entry_id)

    assert result is True
    assert mock_config_entry.entry_id not in hass.data.get(DOMAIN, {})
