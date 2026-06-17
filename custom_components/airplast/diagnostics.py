"""Diagnostics for the Airplast integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_TOKEN, CONF_USERNAME, DATA_COORDINATOR, DOMAIN
from .coordinator import AirplastCoordinator

_REDACTED = "**REDACTED**"
_REDACTED_KEYS = {CONF_TOKEN, "password", "jwtToken", "token"}


def _redact(data: Any) -> Any:
    if isinstance(data, dict):
        return {
            k: _REDACTED if k in _REDACTED_KEYS else _redact(v)
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [_redact(item) for item in data]
    return data


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    coordinator: AirplastCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]

    device_summary: dict[str, Any] = {}
    if coordinator.data:
        for house_id, house_data in coordinator.data.items():
            devices = house_data.get("devices", {})
            device_summary[str(house_id)] = {
                "device_count": len(devices),
                "serials": list(devices.keys()),
                "status_fields": (
                    list(devices[next(iter(devices))]["status"].model_fields_set)
                    if devices
                    else []
                ),
            }

    return {
        "entry_data": _redact(dict(entry.data)),
        "entry_options": _redact(dict(entry.options)),
        "last_update_success": coordinator.last_update_success,
        "last_exception": str(coordinator.last_exception) if coordinator.last_exception else None,
        "houses": device_summary,
    }
