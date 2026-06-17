"""Select platform for Airplast integration.

Exposes per-device write controls that correspond to sliders in the app:
- Humidity level (Dry / Normal / Moist) — available on modes that support it
- Light sensor level (Off / Low / Medium) — only shown when device has a twilight sensor
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import (
    AirplastRequestError,
    ChangeModeRequest,
    FanSpeed,
    HumidityLevel,
    LightSensorLevelEnum,
    OperatingMode,
)
from .const import DATA_CLIENT, DATA_COORDINATOR, DOMAIN, FAN_SPEED_ORDERED, OPERATING_MODE_LABELS
from .api import AirplastHAClient
from .coordinator import AirplastCoordinator
from .entity import AirplastEntity

_LOGGER = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Capability maps (from app source: ZoneView capability matrix)
# Modes where each control is active:
# ------------------------------------------------------------------

# Modes where humidityLevel slider is enabled
_HUMIDITY_MODES = {
    OperatingMode.AUTO,
    OperatingMode.SURVEILLANCE,
}

# Modes where lightSensorLevel slider is enabled (when device supports it)
_LIGHT_MODES = {
    OperatingMode.SMART,
    OperatingMode.AUTO,
}

HUMIDITY_OPTIONS = ["Dry", "Normal", "Moist"]
HUMIDITY_TO_ENUM = {
    "Dry": HumidityLevel.DRY,
    "Normal": HumidityLevel.NORMAL,
    "Moist": HumidityLevel.MOIST,
}

LIGHT_OPTIONS = ["Off", "Low", "Medium"]
LIGHT_TO_ENUM = {
    "Off": LightSensorLevelEnum.OFF,
    "Low": LightSensorLevelEnum.LOW,
    "Medium": LightSensorLevelEnum.MEDIUM,
}

FAN_SPEED_OPTIONS = [
    speed.value if hasattr(speed, "value") else str(speed)
    for speed in FAN_SPEED_ORDERED
]

FAN_SPEED_TO_ENUM = {
    speed.value if hasattr(speed, "value") else str(speed): speed
    for speed in FAN_SPEED_ORDERED
}

OPERATING_MODE_OPTIONS = [
    mode.value if hasattr(mode, "value") else str(mode)
    for mode in OPERATING_MODE_LABELS
]

OPERATING_MODE_TO_ENUM = {
    mode.value if hasattr(mode, "value") else str(mode): mode
    for mode in OPERATING_MODE_LABELS
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AirplastCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    client: AirplastHAClient = hass.data[DOMAIN][entry.entry_id][DATA_CLIENT]

    known_serials: set[str] = set()

    def _add_new_entities() -> None:
        if not coordinator.data:
            return
        new_entities: list[_AirplastSelectBase] = []
        for serial in (
            serial
            for house_data in coordinator.data.values()
            for serial in house_data.get("devices", {})
        ):
            if serial not in known_serials:
                known_serials.add(serial)
                new_entities.append(AirplastOperatingModeSelect(coordinator, client, serial))
                new_entities.append(AirplastFanSpeedSelect(coordinator, client, serial))
                new_entities.append(AirplastHumiditySelect(coordinator, client, serial))
                new_entities.append(AirplastLightSensorSelect(coordinator, client, serial))
        if new_entities:
            async_add_entities(new_entities)

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


# ------------------------------------------------------------------
# Base select entity
# ------------------------------------------------------------------


class _AirplastSelectBase(AirplastEntity, SelectEntity):
    """Shared logic for Airplast select entities that send ChangeModeRequest."""

    def __init__(
        self,
        coordinator: AirplastCoordinator,
        client: AirplastHAClient,
        serial_number: str,
        entity_kind: str,
    ) -> None:
        super().__init__(coordinator, serial_number, entity_kind)
        self._client = client

    async def _send_change(self, **overrides: Any) -> None:
        """Send a ChangeModeRequest, preserving all other current status fields."""
        status = self._status
        if status is None:
            raise HomeAssistantError("Device status unavailable")

        payload = {
            "deviceSerialNumber": self._serial_number,
            "operatingMode": status.operatingMode,
            "fanSpeed": status.fanSpeed,
            "humidityLevel": status.humidityLevel,
            "lightSensorLevel": status.lightSensorLevel,
            "isScheduleMode": False,
        }
        payload.update(overrides)
        request = ChangeModeRequest(**payload)
        try:
            success = await self._client.async_change_working_mode(request)
        except AirplastRequestError as exc:
            raise HomeAssistantError(f"Failed to send command: {exc}") from exc
        if not success:
            raise HomeAssistantError(f"Command returned non-OK for device {self._serial_number}")
        await self.coordinator.async_request_refresh()


# ------------------------------------------------------------------
# Humidity level select
# ------------------------------------------------------------------


class AirplastHumiditySelect(_AirplastSelectBase):
    """Select entity for humidity level (Dry / Normal / Moist)."""

    _attr_name = "Humidity Level"
    _attr_options = HUMIDITY_OPTIONS
    _attr_icon = "mdi:water-percent"

    def __init__(
        self,
        coordinator: AirplastCoordinator,
        client: AirplastHAClient,
        serial_number: str,
    ) -> None:
        super().__init__(coordinator, client, serial_number, "select_humidity_level")

    @property
    def current_option(self) -> str | None:
        status = self._status
        if status is None or status.humidityLevel is None:
            return None
        return status.humidityLevel.value

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        status = self._status
        if status is None or status.operatingMode is None:
            return False
        return status.operatingMode in _HUMIDITY_MODES

    async def async_select_option(self, option: str) -> None:
        level = HUMIDITY_TO_ENUM.get(option)
        if level is None:
            raise HomeAssistantError(f"Unknown humidity level: {option}")
        await self._send_change(humidityLevel=level)


# ------------------------------------------------------------------
# Light sensor level select
# ------------------------------------------------------------------


class AirplastLightSensorSelect(_AirplastSelectBase):
    """Select entity for twilight/light sensor level (Off / Low / Medium).

    Only created for devices that report a non-NotAvailable lightSensorLevel.
    """

    _attr_name = "Light Sensor Level"
    _attr_options = LIGHT_OPTIONS
    _attr_icon = "mdi:brightness-6"

    def __init__(
        self,
        coordinator: AirplastCoordinator,
        client: AirplastHAClient,
        serial_number: str,
    ) -> None:
        super().__init__(coordinator, client, serial_number, "select_light_sensor_level")

    @property
    def current_option(self) -> str | None:
        status = self._status
        if status is None or status.lightSensorLevel is None:
            return None
        if status.lightSensorLevel == LightSensorLevelEnum.NOT_AVAILABLE:
            return None
        return status.lightSensorLevel.value

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        status = self._status
        if status is None or status.lightSensorLevel is None:
            return False
        if status.lightSensorLevel == LightSensorLevelEnum.NOT_AVAILABLE:
            return False
        return status.operatingMode in _LIGHT_MODES

    async def async_select_option(self, option: str) -> None:
        level = LIGHT_TO_ENUM.get(option)
        if level is None:
            raise HomeAssistantError(f"Unknown light sensor level: {option}")
        await self._send_change(lightSensorLevel=level)


# ------------------------------------------------------------------
# Fan speed select
# ------------------------------------------------------------------


class AirplastFanSpeedSelect(_AirplastSelectBase):
    """Select entity for explicit fan speed control."""

    _attr_name = "Fan Speed"
    _attr_options = FAN_SPEED_OPTIONS
    _attr_icon = "mdi:fan-speed-3"

    def __init__(
        self,
        coordinator: AirplastCoordinator,
        client: AirplastHAClient,
        serial_number: str,
    ) -> None:
        super().__init__(coordinator, client, serial_number, "select_fan_speed")

    @property
    def current_option(self) -> str | None:
        status = self._status
        if status is None or status.fanSpeed is None:
            return None
        return status.fanSpeed.value

    async def async_select_option(self, option: str) -> None:
        speed = FAN_SPEED_TO_ENUM.get(option)
        if speed is None:
            raise HomeAssistantError(f"Unknown fan speed: {option}")
        await self._send_change(fanSpeed=speed)


# ------------------------------------------------------------------
# Operating mode select
# ------------------------------------------------------------------


class AirplastOperatingModeSelect(_AirplastSelectBase):
    """Select entity for explicit operating mode control."""

    _attr_name = "Operating Mode"
    _attr_options = OPERATING_MODE_OPTIONS
    _attr_icon = "mdi:tune-variant"

    def __init__(
        self,
        coordinator: AirplastCoordinator,
        client: AirplastHAClient,
        serial_number: str,
    ) -> None:
        super().__init__(coordinator, client, serial_number, "select_operating_mode")

    @property
    def current_option(self) -> str | None:
        status = self._status
        if status is None or status.operatingMode is None:
            return None
        return status.operatingMode.value

    async def async_select_option(self, option: str) -> None:
        mode = OPERATING_MODE_TO_ENUM.get(option)
        if mode is None:
            raise HomeAssistantError(f"Unknown operating mode: {option}")
        await self._send_change(operatingMode=mode)
