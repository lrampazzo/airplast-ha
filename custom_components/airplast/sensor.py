"""Sensor platform for Airplast integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, SIGNAL_STRENGTH_DECIBELS_MILLIWATT, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import StatusPacket

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import AirplastCoordinator
from .entity import AirplastEntity


@dataclass(frozen=True)
class AirplastSensorEntityDescription(SensorEntityDescription):
    value_fn: Callable[[StatusPacket], Any] | None = None


SENSORS: tuple[AirplastSensorEntityDescription, ...] = (
    AirplastSensorEntityDescription(
        key="temperature",
        name="Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda s: s.temperature,
    ),
    AirplastSensorEntityDescription(
        key="humidity",
        name="Humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda s: s.humidity,
    ),
    AirplastSensorEntityDescription(
        key="air_quality",
        name="Air Quality",
        icon="mdi:air-filter",
        value_fn=lambda s: s.airQuality.value if s.airQuality else None,
    ),
    AirplastSensorEntityDescription(
        key="operating_mode",
        name="Operating Mode",
        icon="mdi:fan",
        value_fn=lambda s: s.operatingMode.value if s.operatingMode else None,
    ),
    AirplastSensorEntityDescription(
        key="fan_speed",
        name="Fan Speed",
        icon="mdi:fan-chevron-up",
        value_fn=lambda s: s.fanSpeed.value if s.fanSpeed else None,
    ),
    AirplastSensorEntityDescription(
        key="humidity_level",
        name="Humidity Level",
        icon="mdi:water-percent",
        value_fn=lambda s: s.humidityLevel.value if s.humidityLevel else None,
    ),
    AirplastSensorEntityDescription(
        key="filter_status",
        name="Filter Status",
        icon="mdi:air-filter",
        value_fn=lambda s: s.filtersStatus.value if s.filtersStatus else None,
    ),
    AirplastSensorEntityDescription(
        key="signal_strength",
        name="Signal Strength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        entity_registry_enabled_default=False,
        value_fn=lambda s: s.signalStrenght,  # note: API typo preserved
    ),
    AirplastSensorEntityDescription(
        key="schedule_state",
        name="Schedule State",
        icon="mdi:calendar-clock",
        entity_registry_enabled_default=False,
        value_fn=lambda s: s.isScheduled.value if s.isScheduled else None,
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
        new_entities: list[AirplastSensorEntity] = []
        for house_data in coordinator.data.values():
            for serial in house_data.get("devices", {}):
                if serial not in known_serials:
                    known_serials.add(serial)
                    for description in SENSORS:
                        new_entities.append(AirplastSensorEntity(coordinator, serial, description))
        if new_entities:
            async_add_entities(new_entities)

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


class AirplastSensorEntity(AirplastEntity, SensorEntity):
    """A single Airplast sensor."""

    entity_description: AirplastSensorEntityDescription

    def __init__(
        self,
        coordinator: AirplastCoordinator,
        serial_number: str,
        description: AirplastSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, serial_number, f"sensor_{description.key}")
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        status = self._status
        if status is None or self.entity_description.value_fn is None:
            return None
        return self.entity_description.value_fn(status)
