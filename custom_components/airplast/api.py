"""Airplast Home Assistant integration – HA convenience facade.

Wraps ``AirplastApiClient`` and adds:
- session-aware instantiation helpers
- opportunistic token refresh
- typed error translation into HA exceptions
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import (
    AirplastApiClient,
    AirplastAuthError,
    AirplastRequestError,
    AuthenticateRequest,
    ChangeModeRequest,
    HouseDevicesInfo,
    HouseInfo,
)
from .client.openapi_models import AuthenticateResponse, TokenRefreshResponse

from .const import DEFAULT_BASE_URL

_LOGGER = logging.getLogger(__name__)

# Refresh token when fewer than this many seconds remain before expiry.
_TOKEN_REFRESH_THRESHOLD_S = 300


class AirplastHAClient:
    """Home Assistant convenience wrapper around ``AirplastApiClient``.

    - Stores the token in memory; HA config entry owns persistence.
    - Provides ``async_ensure_token`` to refresh opportunistically before
      each coordinator poll.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        username: str,
        token: str,
        token_expiry: datetime | None,
        base_url: str = DEFAULT_BASE_URL,
        verify_ssl: bool = True,
    ) -> None:
        self._username = username
        self._token_expiry = token_expiry
        session: aiohttp.ClientSession = async_get_clientsession(hass, verify_ssl=verify_ssl)
        self._client = AirplastApiClient(
            base_url=base_url,
            token=token,
            verify_ssl=verify_ssl,
            session=session,
        )

    # ------------------------------------------------------------------
    # Token lifecycle
    # ------------------------------------------------------------------

    def set_token(self, token: str, expiry: datetime | None = None) -> None:
        self._client.set_token(token)
        self._token_expiry = expiry

    def get_token(self) -> str | None:
        return self._client.get_token()

    @property
    def token_near_expiry(self) -> bool:
        if self._token_expiry is None:
            return False
        now = datetime.now(tz=timezone.utc)
        remaining = (self._token_expiry - now).total_seconds()
        return remaining < _TOKEN_REFRESH_THRESHOLD_S

    async def async_ensure_token(self) -> None:
        """Opportunistically refresh token if near expiry.

        Raises ``ConfigEntryAuthFailed`` if refresh fails so HA can
        surface a reauth flow.
        """
        if not self.token_near_expiry:
            return
        _LOGGER.debug("Airplast token near expiry, attempting refresh")
        try:
            resp = await self._client.refresh_token()
        except AirplastRequestError as exc:
            raise ConfigEntryAuthFailed(f"Token refresh transport error: {exc}") from exc

        if not resp.ok:
            raise ConfigEntryAuthFailed(
                f"Token refresh failed with status {resp.status_code}"
            )

        data = resp.json() or {}
        new_token = data.get("token")
        if not new_token:
            raise ConfigEntryAuthFailed("Token refresh returned no token")

        expiry: datetime | None = None
        if valid_to := data.get("validTo"):
            try:
                expiry = datetime.fromisoformat(valid_to.replace("Z", "+00:00"))
            except ValueError:
                pass

        self.set_token(new_token, expiry)
        _LOGGER.debug("Airplast token refreshed, new expiry: %s", expiry)

    # ------------------------------------------------------------------
    # HA-oriented convenience methods
    # ------------------------------------------------------------------

    async def async_login(self, password: str) -> AuthenticateResponse:
        """Authenticate and store the resulting token.

        Raises ``AirplastAuthError`` on HTTP 401/403 and
        ``AirplastRequestError`` on transport failures.
        """
        resp = await self._client.authenticate(
            AuthenticateRequest(username=self._username, password=password)
        )
        if resp.status_code in (401, 403):
            raise AirplastAuthError("Invalid credentials")
        if not resp.ok:
            raise AirplastRequestError(f"Authenticate returned {resp.status_code}")

        data = resp.json() or {}
        token = data.get("jwtToken")
        if not token:
            raise AirplastAuthError("No jwtToken in authenticate response")

        expiry: datetime | None = None
        if expires_at := data.get("expiresAt"):
            try:
                expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            except ValueError:
                pass

        self.set_token(token, expiry)
        return AuthenticateResponse.model_validate(data)

    async def async_get_houses_info(self) -> list[HouseInfo]:
        """Return summary info for all houses belonging to the account."""
        await self.async_ensure_token()
        resp = await self._client.get_houses_info()
        if resp.status_code in (401, 403):
            raise ConfigEntryAuthFailed("Unauthorized when fetching houses info")
        resp.json()  # validate parseable; coordinator handles errors
        data = resp.json()
        if isinstance(data, list):
            return [HouseInfo.model_validate(h) for h in data]
        return []

    async def async_get_house_devices_status(self, house_id: int) -> HouseDevicesInfo:
        """Return live device status for all devices in a house."""
        await self.async_ensure_token()
        resp = await self._client.get_house_devices_status(house_id)
        if resp.status_code in (401, 403):
            raise ConfigEntryAuthFailed("Unauthorized when fetching device status")
        if not resp.ok:
            raise AirplastRequestError(
                f"house-devices-status returned {resp.status_code} for house {house_id}"
            )
        return HouseDevicesInfo.model_validate(resp.json() or {})

    async def async_get_house_devices(self, house_id: int) -> list[dict]:
        """Return device metadata list for enrichment (names, rooms, firmware)."""
        await self.async_ensure_token()
        resp = await self._client.get_house_devices(house_id)
        if not resp.ok:
            _LOGGER.warning("house-devices returned %s for house %s", resp.status_code, house_id)
            return []
        data = resp.json()
        return data if isinstance(data, list) else []

    async def async_change_working_mode(self, request: ChangeModeRequest) -> bool:
        """Send a change-mode command. Returns True on success."""
        await self.async_ensure_token()
        resp = await self._client.change_mode(request)
        if resp.status_code in (401, 403):
            raise ConfigEntryAuthFailed("Unauthorized when sending change-mode command")
        return resp.ok

    async def async_reset_filter(self, device_serial_number: str) -> bool:
        """Send a filter-reset command. Returns True on success."""
        await self.async_ensure_token()
        resp = await self._client.reset_filter(device_serial_number)
        if resp.status_code in (401, 403):
            raise ConfigEntryAuthFailed("Unauthorized when sending reset-filter command")
        return resp.ok
