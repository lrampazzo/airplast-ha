"""Binary sensor platform for Airplast integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import StatusPacket

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import AirplastCoordinator
from .entity import AirplastEntity


@dataclass(frozen=True)
class AirplastBinarySensorEntityDescription(BinarySensorEntityDescription):
    value_fn: Callable[[StatusPacket], bool | None] | None = None


BINARY_SENSORS: tuple[AirplastBinarySensorEntityDescription, ...] = (
    AirplastBinarySensorEntityDescription(
        key="humidity_alarm",
        name="Humidity Alarm",
        device_class=BinarySensorDeviceClass.MOISTURE,
        value_fn=lambda s: s.humidityAlarm,
    ),
    AirplastBinarySensorEntityDescription(
        key="twilight_sensor",
        name="Twilight Sensor",
        icon="mdi:weather-sunset-down",
        value_fn=lambda s: s.nightAlarm,
    ),
    AirplastBinarySensorEntityDescription(
        key="turbo_available",
        name="Turbo Available",
        icon="mdi:fan-plus",
        value_fn=lambda s: s.isTurboAvailable,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AirplastCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]

    known_serials: set[str] = set()

    def _add_new_entities() -> None:
        if not coordinator.data:
            return
        new_entities: list[AirplastBinarySensorEntity] = []
        for house_data in coordinator.data.values():
            for serial in house_data.get("devices", {}):
                if serial not in known_serials:
                    known_serials.add(serial)
                    for description in BINARY_SENSORS:
                        new_entities.append(AirplastBinarySensorEntity(coordinator, serial, description))
        if new_entities:
            async_add_entities(new_entities)

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


class AirplastBinarySensorEntity(AirplastEntity, BinarySensorEntity):
    """A single Airplast binary sensor."""

    entity_description: AirplastBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: AirplastCoordinator,
        serial_number: str,
        description: AirplastBinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, serial_number, f"binary_{description.key}")
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        status = self._status
        if status is None or self.entity_description.value_fn is None:
            return None
        return self.entity_description.value_fn(status)
