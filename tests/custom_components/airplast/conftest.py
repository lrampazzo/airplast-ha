"""Shared fixtures for custom_components/airplast tests."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.airplast.const import (
    CONF_BASE_URL,
    CONF_POLLING_INTERVAL,
    CONF_TOKEN,
    CONF_TOKEN_EXPIRY,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DATA_CLIENT,
    DATA_COORDINATOR,
    DEFAULT_BASE_URL,
    DOMAIN,
)

# ---------------------------------------------------------------------------
# Sample API responses
# ---------------------------------------------------------------------------

MOCK_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
MOCK_USERNAME = "test@example.com"
MOCK_HOUSE_ID = 42
MOCK_SERIAL = "SN123456"
MOCK_SERIAL_2 = "SN654321"

MOCK_AUTH_RESPONSE = {
    "id": 1,
    "firstName": "Test",
    "lastName": "User",
    "username": MOCK_USERNAME,
    "jwtToken": MOCK_TOKEN,
    "expiresAt": "2030-01-01T00:00:00Z",
    "userLevel": 1,
}

MOCK_HOUSES_INFO_RESPONSE = [
    {
        "houseId": MOCK_HOUSE_ID,
        "houseName": "My House",
        "houseZonesCount": 1,
        "houseDevicesCount": 1,
    }
]

MOCK_STATUS_PACKET = {
    "deviceSerialNumber": MOCK_SERIAL,
    "operatingMode": "Auto",
    "fanSpeed": "Medium",
    "humidityLevel": "Normal",
    "temperature": 22,
    "humidity": 55,
    "airQuality": "Good",
    "humidityAlarm": False,
    "filtersStatus": "Good",
    "nightAlarm": False,
    "signalStrenght": -60,
    "isScheduled": "Off",
    "isTurboAvailable": True,
    "lightSensorLevel": "NotAvailable",
    "packetType": "Status",
    "deviceType": "Gemini",
    "deviceSubtype": "Version200",
    "deviceRole": "Master",
    "lastOperatingMode": "Auto",
}

MOCK_HOUSE_DEVICES_STATUS_RESPONSE = {
    "geminiDevicesInfo": [
        {
            "device": {
                "id": 1,
                "serialNumber": MOCK_SERIAL,
                "name": "Living Room",
                "deviceType": "Gemini",
                "deviceSubtype": "Version200",
                "userId": 1,
                "role": "Master",
                "microFwVersion": "1.2.3",
                "radioFwVersion": "4.5.6",
            },
            "statusPacket": MOCK_STATUS_PACKET,
        }
    ],
    "zoneDevicesInfo": [],
    "uniqueZoneDevicesCount": 0,
    "masterSn": MOCK_SERIAL,
}

# ---------------------------------------------------------------------------
# Config entry fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mock Airplast config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_USERNAME,
        title=MOCK_USERNAME,
        data={
            CONF_USERNAME: MOCK_USERNAME,
            CONF_BASE_URL: DEFAULT_BASE_URL,
            CONF_TOKEN: MOCK_TOKEN,
            CONF_TOKEN_EXPIRY: "2030-01-01T00:00:00+00:00",
        },
        options={
            CONF_POLLING_INTERVAL: 60,
            CONF_VERIFY_SSL: True,
        },
    )


# ---------------------------------------------------------------------------
# Mock AirplastHAClient
# ---------------------------------------------------------------------------


def build_mock_ha_client(
    houses_info: list | None = None,
    house_devices_status: dict | None = None,
    change_mode_ok: bool = True,
) -> MagicMock:
    """Return a pre-configured mock AirplastHAClient."""
    from custom_components.airplast.client import HouseDevicesInfo, HouseInfo

    if houses_info is None:
        houses_info = MOCK_HOUSES_INFO_RESPONSE
    if house_devices_status is None:
        house_devices_status = MOCK_HOUSE_DEVICES_STATUS_RESPONSE

    client = MagicMock()
    client.get_token.return_value = MOCK_TOKEN
    client.token_near_expiry = False
    client.async_ensure_token = AsyncMock()
    client.async_login = AsyncMock()
    client.async_get_houses_info = AsyncMock(
        return_value=[HouseInfo.model_validate(h) for h in houses_info]
    )
    client.async_get_house_devices_status = AsyncMock(
        return_value=HouseDevicesInfo.model_validate(house_devices_status)
    )
    client.async_get_house_devices = AsyncMock(return_value=[])
    client.async_change_working_mode = AsyncMock(return_value=change_mode_ok)
    return client


@pytest.fixture
def mock_ha_client() -> MagicMock:
    return build_mock_ha_client()
