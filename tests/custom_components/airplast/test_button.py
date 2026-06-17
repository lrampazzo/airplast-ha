"""Button entity tests for the Airplast integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.airplast.button import AirplastResetFilterButton
from custom_components.airplast.client import AirplastRequestError, FilterStatus
from custom_components.airplast.coordinator import AirplastCoordinator

from .test_entities import _make_full_status
from .conftest import MOCK_SERIAL, build_mock_ha_client


def _hass() -> MagicMock:
    hass = MagicMock()
    hass.loop = __import__("asyncio").get_event_loop()
    return hass


def _make_button(filter_status: FilterStatus = FilterStatus.GOOD):
    client = build_mock_ha_client()
    coordinator = AirplastCoordinator(_hass(), client, polling_interval=60)
    coordinator.data = {
        1: {
            "devices": {
                MOCK_SERIAL: {
                    "status": _make_full_status(filtersStatus=filter_status),
                    "meta": None,
                    "house_id": 1,
                    "house_name": "My House",
                }
            },
            "house_info": None,
        }
    }
    button = AirplastResetFilterButton(coordinator, client, MOCK_SERIAL)
    return coordinator, client, button


async def test_reset_filter_button_available_when_filter_good() -> None:
    _, _, button = _make_button(FilterStatus.GOOD)
    assert button.available is True


async def test_reset_filter_button_available_when_filter_bad() -> None:
    _, _, button = _make_button(FilterStatus.BAD)
    assert button.available is True


async def test_reset_filter_button_press_calls_api() -> None:
    coordinator, client, button = _make_button(FilterStatus.GOOD)
    client.async_reset_filter = AsyncMock(return_value=True)
    coordinator.async_request_refresh = AsyncMock()

    await button.async_press()

    client.async_reset_filter.assert_awaited_once_with(MOCK_SERIAL)
    coordinator.async_request_refresh.assert_awaited_once()


async def test_reset_filter_button_press_raises_on_transport_error() -> None:
    _, client, button = _make_button(FilterStatus.GOOD)
    client.async_reset_filter = AsyncMock(side_effect=AirplastRequestError("timeout"))

    with pytest.raises(HomeAssistantError):
        await button.async_press()


async def test_reset_filter_button_press_raises_on_non_ok() -> None:
    _, client, button = _make_button(FilterStatus.GOOD)
    client.async_reset_filter = AsyncMock(return_value=False)

    with pytest.raises(HomeAssistantError):
        await button.async_press()
