"""Airplast DataUpdateCoordinator.

Polls ``/Device/house-devices-status`` for each configured house and
enriches device metadata from ``/House/house-devices`` when a device
has no name stored yet.

Coordinator data shape::

    {
        <house_id>: {
            "devices": {
                <serial_number>: {
                    "status": StatusPacket,          # live
                    "meta": Device | None,           # enrichment cache
                    "house_id": int,
                    "house_name": str,
                }
            },
            "house_info": HouseInfo | None,
        }
    }
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import AirplastRequestError, Device, HouseDevicesInfo, HouseInfo, StatusPacket

from .api import AirplastHAClient
from .const import DEFAULT_POLLING_INTERVAL

_LOGGER = logging.getLogger(__name__)


class AirplastCoordinator(DataUpdateCoordinator[dict[int, dict[str, Any]]]):
    """Manage polling and normalization for one Airplast account."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: AirplastHAClient,
        polling_interval: int = DEFAULT_POLLING_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Airplast",
            update_interval=timedelta(seconds=polling_interval),
        )
        self._client = client
        # Cache: house_id → list[Device] from /House/house-devices
        self._device_meta_cache: dict[int, dict[str, Device]] = {}

    # ------------------------------------------------------------------
    # DataUpdateCoordinator interface
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict[int, dict[str, Any]]:
        """Fetch latest state for all houses.

        Raises:
            ConfigEntryAuthFailed: on 401/403 — triggers HA reauth flow.
            UpdateFailed: on transient errors.
        """
        try:
            houses_info: list[HouseInfo] = await self._client.async_get_houses_info()
        except ConfigEntryAuthFailed:
            raise
        except AirplastRequestError as exc:
            raise UpdateFailed(f"Cannot reach Airplast backend: {exc}") from exc
        except Exception as exc:
            raise UpdateFailed(f"Unexpected error fetching houses: {exc}") from exc

        result: dict[int, dict[str, Any]] = {}

        for house_info in houses_info:
            house_id = house_info.houseId
            if house_id is None:
                continue

            # Fetch live device status
            try:
                house_status: HouseDevicesInfo = await self._client.async_get_house_devices_status(house_id)
            except ConfigEntryAuthFailed:
                raise
            except (AirplastRequestError, Exception) as exc:
                _LOGGER.warning("Failed to fetch status for house %s: %s", house_id, exc)
                continue

            # Optionally enrich with device metadata
            if house_id not in self._device_meta_cache:
                await self._refresh_device_meta(house_id)

            devices: dict[str, dict[str, Any]] = {}
            house_name = house_info.houseName or f"House {house_id}"

            # Collect statuses from zone devices
            for zone_info in house_status.zoneDevicesInfo or []:
                packet: StatusPacket | None = zone_info.statusPacket
                if packet and packet.deviceSerialNumber:
                    sn = packet.deviceSerialNumber
                    devices[sn] = {
                        "status": packet,
                        "meta": self._device_meta_cache.get(house_id, {}).get(sn),
                        "house_id": house_id,
                        "house_name": house_name,
                    }

            # Collect statuses from Gemini devices
            for gemini_info in house_status.geminiDevicesInfo or []:
                packet = gemini_info.statusPacket
                device_meta = gemini_info.device
                if packet and packet.deviceSerialNumber:
                    sn = packet.deviceSerialNumber
                    devices[sn] = {
                        "status": packet,
                        "meta": device_meta or self._device_meta_cache.get(house_id, {}).get(sn),
                        "house_id": house_id,
                        "house_name": house_name,
                    }

            # Fallback: uniqueZone status packet
            if not devices and house_status.uniqueZoneStatusPacket:
                packet = house_status.uniqueZoneStatusPacket
                if packet.deviceSerialNumber:
                    sn = packet.deviceSerialNumber
                    devices[sn] = {
                        "status": packet,
                        "meta": self._device_meta_cache.get(house_id, {}).get(sn),
                        "house_id": house_id,
                        "house_name": house_name,
                    }

            result[house_id] = {
                "devices": devices,
                "house_info": house_info,
            }

        return result

    # ------------------------------------------------------------------
    # Metadata enrichment
    # ------------------------------------------------------------------

    async def _refresh_device_meta(self, house_id: int) -> None:
        """Cache device metadata for a house (names, firmware, room)."""
        raw_devices = await self._client.async_get_house_devices(house_id)
        by_sn: dict[str, Device] = {}
        for raw in raw_devices:
            try:
                dev = Device.model_validate(raw)
                if dev.serialNumber:
                    by_sn[dev.serialNumber] = dev
            except Exception:
                pass
        self._device_meta_cache[house_id] = by_sn

    def get_device_entry(self, serial_number: str) -> dict[str, Any] | None:
        """Return the coordinator data entry for a given serial number."""
        if not self.data:
            return None
        for house_data in self.data.values():
            entry = house_data.get("devices", {}).get(serial_number)
            if entry is not None:
                return entry
        return None
