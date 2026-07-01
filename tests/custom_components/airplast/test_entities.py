"""Sensor and binary sensor entity tests for the Airplast integration."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from custom_components.airplast.client import (
    AirQuality,
    DeviceSubtype,
    DeviceType,
    FanSpeed,
    FilterStatus,
    HumidityLevel,
    LightSensorLevel,
    OperatingMode,
    ScheduleState,
    StatusPacket,
)
from custom_components.airplast.coordinator import AirplastCoordinator
from custom_components.airplast.sensor import SENSORS, AirplastSensorEntity
from custom_components.airplast.binary_sensor import BINARY_SENSORS, AirplastBinarySensorEntity
from custom_components.airplast.select import AirplastFanSpeedSelect, AirplastHumiditySelect, AirplastLightSensorSelect
from custom_components.airplast.select import AirplastOperatingModeSelect
from custom_components.airplast.const import DOMAIN

from .conftest import MOCK_SERIAL, build_mock_ha_client


def _hass() -> MagicMock:
    hass = MagicMock()
    hass.loop = __import__("asyncio").get_event_loop()
    return hass



# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_full_status(**overrides) -> StatusPacket:
    defaults = dict(
        deviceSerialNumber=MOCK_SERIAL,
        operatingMode=OperatingMode.SMART,
        fanSpeed=FanSpeed.HIGH,
        humidityLevel=HumidityLevel.NORMAL,
        lightSensorLevel=LightSensorLevel.NOT_AVAILABLE,
        temperature=23,
        humidity=60,
        airQuality=AirQuality.GOOD,
        humidityAlarm=False,
        filtersStatus=FilterStatus.GOOD,
        nightAlarm=False,
        signalStrenght=-55,
        isScheduled=ScheduleState.OFF,
        isTurboAvailable=True,
    )
    defaults.update(overrides)
    return StatusPacket(**defaults)


def _coordinator_with_status(status: StatusPacket) -> AirplastCoordinator:
    client = build_mock_ha_client()
    coordinator = AirplastCoordinator(_hass(), client, polling_interval=60)
    coordinator.data = {
        1: {
            "devices": {
                MOCK_SERIAL: {
                    "status": status,
                    "meta": None,
                    "house_id": 1,
                    "house_name": "My House",
                }
            },
            "house_info": None,
        }
    }
    return coordinator


def _get_sensor(coordinator, key: str) -> AirplastSensorEntity:
    desc = next(d for d in SENSORS if d.key == key)
    return AirplastSensorEntity(coordinator, MOCK_SERIAL, desc)


def _get_binary(coordinator, key: str) -> AirplastBinarySensorEntity:
    desc = next(d for d in BINARY_SENSORS if d.key == key)
    return AirplastBinarySensorEntity(coordinator, MOCK_SERIAL, desc)


# ---------------------------------------------------------------------------
# Sensor: values
# ---------------------------------------------------------------------------


async def test_sensor_temperature() -> None:
    coord = _coordinator_with_status(_make_full_status(temperature=21))
    sensor = _get_sensor(coord, "temperature")
    assert sensor.native_value == 21


async def test_sensor_humidity() -> None:
    coord = _coordinator_with_status(_make_full_status(humidity=48))
    sensor = _get_sensor(coord, "humidity")
    assert sensor.native_value == 48


async def test_sensor_air_quality() -> None:
    coord = _coordinator_with_status(_make_full_status(airQuality=AirQuality.VERY_GOOD))
    sensor = _get_sensor(coord, "air_quality")
    assert sensor.native_value == "VeryGood"


async def test_sensor_operating_mode() -> None:
    coord = _coordinator_with_status(_make_full_status(operatingMode=OperatingMode.NIGHT))
    sensor = _get_sensor(coord, "operating_mode")
    assert sensor.native_value == "Night"


async def test_sensor_fan_speed() -> None:
    coord = _coordinator_with_status(_make_full_status(fanSpeed=FanSpeed.LOW))
    sensor = _get_sensor(coord, "fan_speed")
    assert sensor.native_value == "Low"


async def test_sensor_humidity_level() -> None:
    coord = _coordinator_with_status(_make_full_status(humidityLevel=HumidityLevel.DRY))
    sensor = _get_sensor(coord, "humidity_level")
    assert sensor.native_value == "Dry"


async def test_sensor_filter_status() -> None:
    coord = _coordinator_with_status(_make_full_status(filtersStatus=FilterStatus.BAD))
    sensor = _get_sensor(coord, "filter_status")
    assert sensor.native_value == "Bad"


async def test_sensor_signal_strength() -> None:
    coord = _coordinator_with_status(_make_full_status(signalStrenght=-72))
    sensor = _get_sensor(coord, "signal_strength")
    assert sensor.native_value == -72


async def test_sensor_schedule_state() -> None:
    coord = _coordinator_with_status(_make_full_status(isScheduled=ScheduleState.ON))
    sensor = _get_sensor(coord, "schedule_state")
    assert sensor.native_value == "On"


# ---------------------------------------------------------------------------
# Sensor: None when field absent
# ---------------------------------------------------------------------------


async def test_sensor_returns_none_when_field_absent() -> None:
    status = StatusPacket(deviceSerialNumber=MOCK_SERIAL)  # no temperature
    coord = _coordinator_with_status(status)
    sensor = _get_sensor(coord, "temperature")
    assert sensor.native_value is None


# ---------------------------------------------------------------------------
# Sensor: unavailability
# ---------------------------------------------------------------------------


async def test_sensor_unavailable_when_no_coordinator_data() -> None:
    client = build_mock_ha_client()
    coordinator = AirplastCoordinator(_hass(), client, polling_interval=60)
    coordinator.data = {}
    desc = next(d for d in SENSORS if d.key == "temperature")
    sensor = AirplastSensorEntity(coordinator, MOCK_SERIAL, desc)
    assert sensor.available is False


async def test_sensor_available_when_data_present() -> None:
    coord = _coordinator_with_status(_make_full_status())
    coord.last_update_success = True
    sensor = _get_sensor(coord, "temperature")
    assert sensor.available is True


# ---------------------------------------------------------------------------
# Sensor: unique IDs
# ---------------------------------------------------------------------------


async def test_sensor_unique_id() -> None:
    coord = _coordinator_with_status(_make_full_status())
    sensor = _get_sensor(coord, "temperature")
    assert sensor.unique_id == f"{MOCK_SERIAL}_sensor_temperature"


# ---------------------------------------------------------------------------
# Binary sensor: values
# ---------------------------------------------------------------------------


async def test_binary_sensor_humidity_alarm_on() -> None:
    coord = _coordinator_with_status(_make_full_status(humidityAlarm=True))
    bs = _get_binary(coord, "humidity_alarm")
    assert bs.is_on is True


async def test_binary_sensor_humidity_alarm_off() -> None:
    coord = _coordinator_with_status(_make_full_status(humidityAlarm=False))
    bs = _get_binary(coord, "humidity_alarm")
    assert bs.is_on is False


async def test_binary_sensor_twilight_sensor() -> None:
    coord = _coordinator_with_status(_make_full_status(nightAlarm=True))
    bs = _get_binary(coord, "twilight_sensor")
    assert bs.is_on is True


async def test_binary_sensor_turbo_available() -> None:
    coord = _coordinator_with_status(_make_full_status(isTurboAvailable=True))
    bs = _get_binary(coord, "turbo_available")
    assert bs.is_on is True


async def test_binary_sensor_none_when_no_status() -> None:
    client = build_mock_ha_client()
    coordinator = AirplastCoordinator(_hass(), client, polling_interval=60)
    coordinator.data = {}
    desc = next(d for d in BINARY_SENSORS if d.key == "humidity_alarm")
    bs = AirplastBinarySensorEntity(coordinator, MOCK_SERIAL, desc)
    assert bs.is_on is None


async def test_binary_sensor_unique_id() -> None:
    coord = _coordinator_with_status(_make_full_status())
    bs = _get_binary(coord, "humidity_alarm")
    assert bs.unique_id == f"{MOCK_SERIAL}_binary_humidity_alarm"


async def test_humidity_select_uses_device_serial_for_registry_identity() -> None:
    coord = _coordinator_with_status(_make_full_status())
    client = build_mock_ha_client()
    select = AirplastHumiditySelect(coord, client, MOCK_SERIAL)

    assert select.unique_id == f"{MOCK_SERIAL}_select_humidity_level"
    assert (DOMAIN, MOCK_SERIAL) in select.device_info["identifiers"]


async def test_light_select_uses_device_serial_for_registry_identity() -> None:
    coord = _coordinator_with_status(_make_full_status())
    client = build_mock_ha_client()
    select = AirplastLightSensorSelect(coord, client, MOCK_SERIAL)

    assert select.unique_id == f"{MOCK_SERIAL}_select_light_sensor_level"
    assert (DOMAIN, MOCK_SERIAL) in select.device_info["identifiers"]


async def test_fan_speed_select_uses_device_serial_for_registry_identity() -> None:
    coord = _coordinator_with_status(_make_full_status())
    client = build_mock_ha_client()
    select = AirplastFanSpeedSelect(coord, client, MOCK_SERIAL)

    assert select.unique_id == f"{MOCK_SERIAL}_select_fan_speed"
    assert (DOMAIN, MOCK_SERIAL) in select.device_info["identifiers"]


async def test_fan_speed_select_sends_change_mode_request() -> None:
    coord = _coordinator_with_status(_make_full_status())
    client = build_mock_ha_client()
    select = AirplastFanSpeedSelect(coord, client, MOCK_SERIAL)
    select.coordinator.async_request_refresh = AsyncMock()

    await select.async_select_option("Low")

    req = client.async_change_working_mode.call_args[0][0]
    assert req.fanSpeed == FanSpeed.LOW


async def test_operating_mode_select_uses_device_serial_for_registry_identity() -> None:
    coord = _coordinator_with_status(_make_full_status())
    client = build_mock_ha_client()
    select = AirplastOperatingModeSelect(coord, client, MOCK_SERIAL)

    assert select.unique_id == f"{MOCK_SERIAL}_select_operating_mode"
    assert (DOMAIN, MOCK_SERIAL) in select.device_info["identifiers"]


async def test_operating_mode_select_sends_change_mode_request() -> None:
    coord = _coordinator_with_status(_make_full_status())
    client = build_mock_ha_client()
    select = AirplastOperatingModeSelect(coord, client, MOCK_SERIAL)
    select.coordinator.async_request_refresh = AsyncMock()

    await select.async_select_option("Night")

    req = client.async_change_working_mode.call_args[0][0]
    assert req.operatingMode == OperatingMode.NIGHT


async def test_device_info_hw_version_from_metadata_subtype() -> None:
    coord = _coordinator_with_status(_make_full_status())
    client = build_mock_ha_client()
    select = AirplastOperatingModeSelect(coord, client, MOCK_SERIAL)

    class _Meta:
        name = "Bedroom"
        deviceType = DeviceType.GEMINI
        deviceSubtype = DeviceSubtype.VERSION200
        microFwVersion = "1.0.0"
        radioFwVersion = "2.0.0"

    coord.data[1]["devices"][MOCK_SERIAL]["meta"] = _Meta()
    info = select.device_info

    assert info["model"] == "Gemini"
    assert info["hw_version"] == "Version200"


async def test_device_info_hw_version_falls_back_to_status_subtype() -> None:
    status = _make_full_status(deviceSubtype=DeviceSubtype.VERSION160, deviceType=DeviceType.ICON)
    coord = _coordinator_with_status(status)
    client = build_mock_ha_client()
    select = AirplastOperatingModeSelect(coord, client, MOCK_SERIAL)

    info = select.device_info

    assert info["model"] == "Icon"
    assert info["hw_version"] == "Version160"
