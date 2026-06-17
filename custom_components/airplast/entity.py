"""Shared entity base for Airplast entities."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .client import Device, StatusPacket

from .const import DOMAIN
from .coordinator import AirplastCoordinator


class AirplastEntity(CoordinatorEntity[AirplastCoordinator]):
    """Base class for Airplast entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AirplastCoordinator,
        serial_number: str,
        entity_kind: str,
    ) -> None:
        super().__init__(coordinator)
        self._serial_number = serial_number
        self._entity_kind = entity_kind
        self._attr_unique_id = f"{serial_number}_{entity_kind}"

    # ------------------------------------------------------------------
    # Coordinator data helpers
    # ------------------------------------------------------------------

    @property
    def _device_entry(self) -> dict[str, Any] | None:
        return self.coordinator.get_device_entry(self._serial_number)

    @property
    def _status(self) -> StatusPacket | None:
        entry = self._device_entry
        return entry["status"] if entry else None

    @property
    def _meta(self) -> Device | None:
        entry = self._device_entry
        return entry.get("meta") if entry else None

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        return (
            self.coordinator.last_update_success
            and self._device_entry is not None
            and self._status is not None
        )

    # ------------------------------------------------------------------
    # Device info
    # ------------------------------------------------------------------

    @property
    def device_info(self) -> DeviceInfo:
        meta = self._meta
        status = self._status
        entry = self._device_entry or {}

        name: str = (
            (meta.name if meta and meta.name else None)
            or f"Airplast {self._serial_number[-4:]}"
        )
        house_name: str = entry.get("house_name", "")

        fw_version: str | None = None
        if meta:
            parts = [
                v for v in [meta.microFwVersion, meta.radioFwVersion] if v
            ]
            fw_version = " / ".join(parts) or None

        # Prefer metadata when present, but fall back to status packet values
        # so model/hardware labels still render when house-devices enrichment
        # is partial or temporarily unavailable.
        device_type = meta.deviceType if (meta and meta.deviceType) else (status.deviceType if status else None)
        device_subtype = (
            meta.deviceSubtype
            if (meta and meta.deviceSubtype)
            else (status.deviceSubtype if status else None)
        )

        return DeviceInfo(
            identifiers={(DOMAIN, self._serial_number)},
            name=name,
            manufacturer="Airplast",
            model=device_type.value if device_type else None,
            hw_version=device_subtype.value if device_subtype else None,
            sw_version=fw_version,
            serial_number=self._serial_number,
            suggested_area=house_name or None,
        )
