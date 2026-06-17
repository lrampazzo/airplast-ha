"""Button platform for Airplast integration.

Exposes actionable device controls:
- Filter reset — calls /Device/reset-filter, only enabled when filter is Bad
"""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import AirplastRequestError
from .const import DATA_CLIENT, DATA_COORDINATOR, DOMAIN
from .api import AirplastHAClient
from .coordinator import AirplastCoordinator
from .entity import AirplastEntity

_LOGGER = logging.getLogger(__name__)


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
        new_entities: list[AirplastResetFilterButton] = []
        for house_data in coordinator.data.values():
            for serial in house_data.get("devices", {}):
                if serial not in known_serials:
                    known_serials.add(serial)
                    new_entities.append(
                        AirplastResetFilterButton(coordinator, client, serial)
                    )
        if new_entities:
            async_add_entities(new_entities)

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


class AirplastResetFilterButton(AirplastEntity, ButtonEntity):
    """Button entity to reset the filter status on an Airplast device.

    Keep this control clickable whenever the device is available.
    The backend decides whether a reset is currently applicable.
    """

    _attr_name = "Reset Filter"
    _attr_icon = "mdi:air-filter"

    def __init__(
        self,
        coordinator: AirplastCoordinator,
        client: AirplastHAClient,
        serial_number: str,
    ) -> None:
        super().__init__(coordinator, serial_number, "button_reset_filter")
        self._client = client

    @property
    def available(self) -> bool:
        """Expose reset whenever the device is online and has status."""
        return super().available

    async def async_press(self) -> None:
        try:
            success = await self._client.async_reset_filter(self._serial_number)
        except AirplastRequestError as exc:
            raise HomeAssistantError(f"Failed to reset filter: {exc}") from exc
        if not success:
            raise HomeAssistantError(
                f"reset-filter returned a non-OK status for device {self._serial_number}"
            )
        await self.coordinator.async_request_refresh()
