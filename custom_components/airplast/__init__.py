"""Airplast integration setup."""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .client import AirplastRequestError

from .api import AirplastHAClient
from .const import (
    CONF_BASE_URL,
    CONF_POLLING_INTERVAL,
    CONF_TOKEN,
    CONF_TOKEN_EXPIRY,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DATA_CLIENT,
    DATA_COORDINATOR,
    DEFAULT_BASE_URL,
    DEFAULT_POLLING_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import AirplastCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Airplast from a config entry."""
    username: str = entry.data[CONF_USERNAME]
    token: str = entry.data[CONF_TOKEN]
    base_url: str = entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL)
    raw_expiry: str | None = entry.data.get(CONF_TOKEN_EXPIRY)
    verify_ssl: bool = entry.options.get(CONF_VERIFY_SSL, True)
    polling_interval: int = entry.options.get(CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL)

    token_expiry: datetime | None = None
    if raw_expiry:
        try:
            token_expiry = datetime.fromisoformat(raw_expiry)
        except ValueError:
            pass

    client = AirplastHAClient(
        hass=hass,
        username=username,
        token=token,
        token_expiry=token_expiry,
        base_url=base_url,
        verify_ssl=verify_ssl,
    )

    coordinator = AirplastCoordinator(hass, client, polling_interval)

    try:
        await coordinator.async_config_entry_first_refresh()
    except AirplastRequestError as exc:
        raise ConfigEntryNotReady(f"Cannot reach Airplast backend: {exc}") from exc

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        DATA_CLIENT: client,
        DATA_COORDINATOR: coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
