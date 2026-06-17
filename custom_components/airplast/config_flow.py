"""Config flow for the Airplast integration."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import AirplastApiClient, AirplastAuthError, AirplastRequestError, AuthenticateRequest

from .const import (
    CONF_BASE_URL,
    CONF_POLLING_INTERVAL,
    CONF_TOKEN,
    CONF_TOKEN_EXPIRY,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DEFAULT_BASE_URL,
    DEFAULT_POLLING_INTERVAL,
    DOMAIN,
    MIN_POLLING_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
    }
)

_REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_PASSWORD): str})


class AirplastConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Airplast."""

    VERSION = 1

    def __init__(self) -> None:
        self._username: str = ""
        self._base_url: str = DEFAULT_BASE_URL

    # ------------------------------------------------------------------
    # Initial setup
    # ------------------------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME].strip().lower()
            password = user_input[CONF_PASSWORD]
            base_url = user_input.get(CONF_BASE_URL, DEFAULT_BASE_URL).rstrip("/")

            await self.async_set_unique_id(username)
            self._abort_if_unique_id_configured()

            token, expiry, error = await self._try_authenticate(username, password, base_url)

            if token:
                return self.async_create_entry(
                    title=username,
                    data={
                        CONF_USERNAME: username,
                        CONF_BASE_URL: base_url,
                        CONF_TOKEN: token,
                        CONF_TOKEN_EXPIRY: expiry.isoformat() if expiry else None,
                    },
                )
            errors["base"] = error or "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=_USER_SCHEMA,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Reauth
    # ------------------------------------------------------------------

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> dict[str, Any]:
        self._username = entry_data.get(CONF_USERNAME, "")
        self._base_url = entry_data.get(CONF_BASE_URL, DEFAULT_BASE_URL)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        errors: dict[str, str] = {}

        if user_input is not None:
            password = user_input[CONF_PASSWORD]
            token, expiry, error = await self._try_authenticate(
                self._username, password, self._base_url
            )

            if token:
                entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
                if entry:
                    self.hass.config_entries.async_update_entry(
                        entry,
                        data={
                            **entry.data,
                            CONF_TOKEN: token,
                            CONF_TOKEN_EXPIRY: expiry.isoformat() if expiry else None,
                        },
                    )
                return self.async_abort(reason="reauth_successful")
            errors["base"] = error or "unknown"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_REAUTH_SCHEMA,
            errors=errors,
            description_placeholders={"username": self._username},
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _try_authenticate(
        self, username: str, password: str, base_url: str
    ) -> tuple[str | None, datetime | None, str | None]:
        """Return (token, expiry, error_key) tuple."""
        session = async_get_clientsession(self.hass)
        client = AirplastApiClient(base_url=base_url, session=session)
        try:
            resp = await client.authenticate(
                AuthenticateRequest(username=username, password=password)
            )
        except AirplastRequestError:
            return None, None, "cannot_connect"

        if resp.status_code in (401, 403):
            return None, None, "invalid_auth"
        if not resp.ok:
            return None, None, "cannot_connect"

        data = resp.json() or {}
        token: str | None = data.get("jwtToken")
        if not token:
            return None, None, "invalid_auth"

        expiry: datetime | None = None
        if expires_at := data.get("expiresAt"):
            try:
                expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            except ValueError:
                pass

        return token, expiry, None

    # ------------------------------------------------------------------
    # Options
    # ------------------------------------------------------------------

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> "AirplastOptionsFlow":
        return AirplastOptionsFlow(config_entry)


class AirplastOptionsFlow(OptionsFlow):
    """Handle Airplast integration options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if user_input is not None:
            polling = max(MIN_POLLING_INTERVAL, int(user_input.get(CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL)))
            return self.async_create_entry(
                title="",
                data={
                    CONF_POLLING_INTERVAL: polling,
                    CONF_VERIFY_SSL: user_input.get(CONF_VERIFY_SSL, True),
                },
            )

        current = self._config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_POLLING_INTERVAL,
                    default=current.get(CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL),
                ): vol.All(int, vol.Range(min=MIN_POLLING_INTERVAL)),
                vol.Optional(
                    CONF_VERIFY_SSL,
                    default=current.get(CONF_VERIFY_SSL, True),
                ): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
