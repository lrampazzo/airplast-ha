"""Coordinator tests for the Airplast integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.airplast.client import (
    AirplastRequestError,
    ChangeModeRequest,
    FanSpeed,
    OperatingMode,
)
from custom_components.airplast.coordinator import AirplastCoordinator

from .conftest import (
    MOCK_HOUSE_ID,
    MOCK_SERIAL,
    build_mock_ha_client,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hass() -> MagicMock:
    """Return a minimal mock HomeAssistant instance."""
    hass = MagicMock()
    hass.loop = __import__("asyncio").get_event_loop()
    return hass


def _make_coordinator(client=None) -> AirplastCoordinator:
    if client is None:
        client = build_mock_ha_client()
    return AirplastCoordinator(_hass(), client, polling_interval=60)


# ---------------------------------------------------------------------------
# Successful update
# ---------------------------------------------------------------------------


async def test_coordinator_update_populates_data() -> None:
    coordinator = _make_coordinator()
    data = await coordinator._async_update_data()

    assert MOCK_HOUSE_ID in data
    devices = data[MOCK_HOUSE_ID]["devices"]
    assert MOCK_SERIAL in devices
    entry = devices[MOCK_SERIAL]
    assert entry["status"].operatingMode == OperatingMode.AUTO
    assert entry["status"].temperature == 22
    assert entry["house_id"] == MOCK_HOUSE_ID
    assert entry["house_name"] == "My House"


async def test_coordinator_get_device_entry() -> None:
    coordinator = _make_coordinator()
    coordinator.data = await coordinator._async_update_data()

    entry = coordinator.get_device_entry(MOCK_SERIAL)
    assert entry is not None
    assert entry["status"].deviceSerialNumber == MOCK_SERIAL


async def test_coordinator_get_device_entry_unknown() -> None:
    coordinator = _make_coordinator()
    coordinator.data = await coordinator._async_update_data()

    assert coordinator.get_device_entry("UNKNOWN_SN") is None


# ---------------------------------------------------------------------------
# Zone-device path
# ---------------------------------------------------------------------------


async def test_coordinator_zone_device_info() -> None:
    zone_status_response = {
        "zoneDevicesInfo": [
            {
                "statusPacket": {
                    "deviceSerialNumber": "SN_ZONE",
                    "operatingMode": "Night",
                    "fanSpeed": "Low",
                    "temperature": 18,
                    "humidity": 50,
                },
                "zoneDevicesCount": 1,
                "masterSn": "SN_ZONE",
            }
        ],
        "geminiDevicesInfo": [],
    }
    client = build_mock_ha_client(house_devices_status=zone_status_response)
    coordinator = _make_coordinator(client)
    data = await coordinator._async_update_data()

    devices = data[MOCK_HOUSE_ID]["devices"]
    assert "SN_ZONE" in devices
    assert devices["SN_ZONE"]["status"].operatingMode == OperatingMode.NIGHT


# ---------------------------------------------------------------------------
# Auth failures
# ---------------------------------------------------------------------------


async def test_coordinator_raises_auth_failed_on_houses() -> None:
    client = build_mock_ha_client()
    client.async_get_houses_info = AsyncMock(
        side_effect=ConfigEntryAuthFailed("token expired")
    )
    coordinator = _make_coordinator(client)

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_coordinator_raises_auth_failed_on_status() -> None:
    client = build_mock_ha_client()
    client.async_get_house_devices_status = AsyncMock(
        side_effect=ConfigEntryAuthFailed("401")
    )
    coordinator = _make_coordinator(client)

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


# ---------------------------------------------------------------------------
# Transient failures
# ---------------------------------------------------------------------------


async def test_coordinator_raises_update_failed_on_transport() -> None:
    client = build_mock_ha_client()
    client.async_get_houses_info = AsyncMock(
        side_effect=AirplastRequestError("connection refused")
    )
    coordinator = _make_coordinator(client)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_coordinator_skips_failed_house_status() -> None:
    client = build_mock_ha_client()
    client.async_get_house_devices_status = AsyncMock(
        side_effect=AirplastRequestError("timeout")
    )
    coordinator = _make_coordinator(client)
    data = await coordinator._async_update_data()

    assert data == {}


# ---------------------------------------------------------------------------
# Device metadata enrichment
# ---------------------------------------------------------------------------


async def test_coordinator_enriches_device_meta() -> None:
    client = build_mock_ha_client()
    client.async_get_house_devices = AsyncMock(
        return_value=[
            {
                "serialNumber": MOCK_SERIAL,
                "name": "Bedroom",
                "deviceType": "Gemini",
                "deviceSubtype": "Version200",
                "userId": 1,
            }
        ]
    )
    coordinator = _make_coordinator(client)
    coordinator.data = await coordinator._async_update_data()

    entry = coordinator.get_device_entry(MOCK_SERIAL)
    assert entry["meta"] is not None
    # Gemini payload metadata has precedence over enrichment cache.
    assert entry["meta"].name == "Living Room"


async def test_coordinator_device_meta_not_fetched_twice() -> None:
    client = build_mock_ha_client()
    coordinator = _make_coordinator(client)

    await coordinator._async_update_data()
    await coordinator._async_update_data()

    client.async_get_house_devices.assert_called_once()


# ---------------------------------------------------------------------------
# Change mode payload
# ---------------------------------------------------------------------------


async def test_change_mode_request_payload() -> None:
    req = ChangeModeRequest(
        deviceSerialNumber=MOCK_SERIAL,
        operatingMode=OperatingMode.SMART,
        fanSpeed=FanSpeed.HIGH,
        isScheduleMode=False,
    )
    payload = req.model_dump(exclude_none=True, mode="json")
    assert payload["operatingMode"] == "Smart"
    assert payload["fanSpeed"] == "High"
    assert payload["isScheduleMode"] is False
    assert "humidityLevel" not in payload
