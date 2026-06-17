"""Async OpenAPI-aligned Airplast client.

Every public method maps 1-to-1 to an OpenAPI operation and returns an
``AirplastResponse`` without raising on non-2xx responses.  Callers are
responsible for inspecting ``.ok`` and ``.json()``.

Transport errors (network, timeout) raise ``AirplastRequestError``.

Usage – owned session (standalone / scripts)::

    async with AirplastApiClient() as client:
        resp = await client.authenticate(AuthenticateRequest(username="u", password="p"))
        token = resp.json()["jwtToken"]
        client.set_token(token)

Usage – injected session (Home Assistant)::

    client = AirplastApiClient(session=hass_session)
    resp = await client.authenticate(...)
"""

from __future__ import annotations

import json
import ssl
from typing import Any, Mapping

import aiohttp

from .exceptions import AirplastRequestError
from .openapi_models import (
    AddHouseRequest,
    AddNewDeviceRequest,
    AuthenticateRequest,
    ChangeModeRequest,
    ChangeUsernameRequest,
    ConfirmRegisterRequest,
    NewOperationTokenRequest,
    NewZoneWithRoomsRequest,
    RecoverPasswordRequest,
    RegisterRequestWs,
    RenameDeviceRequest,
    RenameHouseRequest,
    RenameZoneRequest,
    ResetDeviceRequest,
    SetHouseTimezoneRequest,
    TimeSlot,
    UpdateFirstLastNameRequest,
    UpdatePasswordRequest,
)

DEFAULT_BASE_URL = "https://sede.airplast.eu:4521"
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=6)
LONG_TIMEOUT = aiohttp.ClientTimeout(total=120)


class AirplastResponse:
    """Wrapper around an aiohttp response, read fully into memory."""

    __slots__ = ("status_code", "headers", "content", "url")

    def __init__(
        self,
        status_code: int,
        headers: Mapping[str, str],
        content: bytes,
        url: str,
    ) -> None:
        self.status_code = status_code
        self.headers = dict(headers)
        self.content = content
        self.url = url

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def text(self) -> str:
        charset = "utf-8"
        content_type = self.headers.get("Content-Type", "")
        for part in content_type.split(";"):
            part = part.strip()
            if part.lower().startswith("charset="):
                charset = part.split("=", 1)[1].strip()
                break
        return self.content.decode(charset, errors="replace")

    def json(self) -> Any:
        if not self.content:
            return None
        return json.loads(self.text)

    def __repr__(self) -> str:
        return f"AirplastResponse(status_code={self.status_code}, url={self.url!r})"


def _model_payload(obj: Any) -> Any:
    """Convert Pydantic models, dicts, and primitives to JSON-serialisable form."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(exclude_none=True, mode="json")
    if hasattr(obj, "__dataclass_fields__"):
        from dataclasses import asdict
        return {k: v for k, v in asdict(obj).items() if v is not None}
    return obj


class AirplastApiClient:
    """Async client for the Airplast backend API (OpenAPI 3.0.4)."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        token: str | None = None,
        timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT,
        verify_ssl: bool = True,
        ssl_context: ssl.SSLContext | None = None,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout
        self._verify_ssl = verify_ssl
        self._ssl_context = ssl_context
        self._session = session
        self._owned_session = session is None

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "AirplastApiClient":
        if self._owned_session:
            connector = aiohttp.TCPConnector(ssl=self._ssl or True)
            self._session = aiohttp.ClientSession(connector=connector)
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._owned_session and self._session is not None:
            await self._session.close()
            self._session = None

    @property
    def _ssl(self) -> ssl.SSLContext | bool:
        if self._ssl_context is not None:
            return self._ssl_context
        return self._verify_ssl

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            raise RuntimeError(
                "No aiohttp session available. "
                "Use 'async with AirplastApiClient() as client:' or inject a session."
            )
        return self._session

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def set_token(self, token: str | None) -> None:
        self._token = token

    def get_token(self) -> str | None:
        return self._token

    def _auth_headers(self, token: str | None = None) -> dict[str, str]:
        t = token if token is not None else self._token
        return {"Authorization": f"Bearer {t}"} if t else {}

    # ------------------------------------------------------------------
    # Core request
    # ------------------------------------------------------------------

    async def request(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, Any] | None = None,
        body: Any = None,
        auth: bool = False,
        token: str | None = None,
        json_body: bool = False,
        extra_headers: Mapping[str, str] | None = None,
        timeout: aiohttp.ClientTimeout | None = None,
    ) -> AirplastResponse:
        url = self._base_url + "/" + path.lstrip("/")
        params = {k: v for k, v in (query or {}).items() if v is not None} or None

        headers: dict[str, str] = {}
        if auth:
            headers.update(self._auth_headers(token))
        if json_body:
            headers["Content-Type"] = "application/json"
        if extra_headers:
            headers.update(extra_headers)

        data: bytes | None = None
        if body is not None:
            data = json.dumps(_model_payload(body), separators=(",", ":")).encode("utf-8")

        session = self._get_session()
        req_timeout = timeout or self._timeout

        try:
            async with session.request(
                method.upper(),
                url,
                params=params,
                data=data,
                headers=headers,
                timeout=req_timeout,
                ssl=self._ssl,
            ) as response:
                content = await response.read()
                return AirplastResponse(
                    status_code=response.status,
                    headers=dict(response.headers),
                    content=content,
                    url=str(response.url),
                )
        except aiohttp.ClientError as exc:
            raise AirplastRequestError(str(exc)) from exc
        except TimeoutError as exc:
            raise AirplastRequestError(f"Request timed out: {exc}") from exc

    # ------------------------------------------------------------------
    # Users endpoints
    # ------------------------------------------------------------------

    async def authenticate(self, request: AuthenticateRequest) -> AirplastResponse:
        return await self.request("POST", "/Users/authenticate", body=request, json_body=True)

    async def get_feature_flags(self) -> AirplastResponse:
        return await self.request("GET", "/Users/feature-flags")

    async def register(self, request: RegisterRequestWs) -> AirplastResponse:
        return await self.request("POST", "/Users/register", body=request, json_body=True)

    async def confirm_registration(self, request: ConfirmRegisterRequest) -> AirplastResponse:
        return await self.request("POST", "/Users/confirmregistration", body=request, json_body=True)

    async def ask_recover_password(self, username: str) -> AirplastResponse:
        return await self.request("GET", "/Users/askrecoverpassword", query={"username": username})

    async def recover_password(self, request: RecoverPasswordRequest) -> AirplastResponse:
        return await self.request("POST", "/Users/recoverpassword", body=request, json_body=True)

    async def refresh_token(self, token: str | None = None) -> AirplastResponse:
        return await self.request("GET", "/Users/refresh-token", auth=True, token=token)

    async def get_token_info(self, token: str | None = None) -> AirplastResponse:
        return await self.request("GET", "/Users/token-info", auth=True, token=token)

    async def get_user_details(self) -> AirplastResponse:
        return await self.request("GET", "/Users/user-details", auth=True)

    async def update_user_details(self, request: UpdateFirstLastNameRequest) -> AirplastResponse:
        return await self.request("POST", "/Users/update-details", body=request, auth=True, json_body=True)

    async def update_password(self, request: UpdatePasswordRequest) -> AirplastResponse:
        return await self.request("POST", "/Users/update-password", body=request, auth=True, json_body=True)

    async def delete_account(self, password: str) -> AirplastResponse:
        return await self.request("DELETE", "/Users/delete", body=password, auth=True, json_body=True)

    async def change_email(self, request: ChangeUsernameRequest) -> AirplastResponse:
        return await self.request("POST", "/Users/change-email", body=request, auth=True, json_body=True)

    async def complete_change_email(self, short_token: str) -> AirplastResponse:
        return await self.request("POST", "/Users/complete-change-email", body=short_token, auth=True, json_body=True)

    async def request_new_changeusername_operation_token(self) -> AirplastResponse:
        return await self.request("GET", "/Users/new-changeusername-operation-token")

    async def request_new_operation_token(self, request: NewOperationTokenRequest) -> AirplastResponse:
        return await self.request("POST", "/Users/new-operation-token", body=request, auth=True, json_body=True)

    # ------------------------------------------------------------------
    # House endpoints
    # ------------------------------------------------------------------

    async def get_houses(self) -> AirplastResponse:
        return await self.request("GET", "/House/houses", auth=True)

    async def get_configured_houses(self) -> AirplastResponse:
        return await self.request("GET", "/House/configured-houses", auth=True)

    async def get_house_info(self, house_id: int) -> AirplastResponse:
        return await self.request("GET", "/House/house-info", query={"houseId": house_id}, auth=True)

    async def get_house_devices(self, house_id: int) -> AirplastResponse:
        return await self.request("GET", "/House/house-devices", query={"houseId": house_id}, auth=True)

    async def add_house(self, request: AddHouseRequest | str) -> AirplastResponse:
        return await self.request("POST", "/House/add-house", body=request, auth=True, json_body=True)

    async def get_houses_info(self) -> AirplastResponse:
        return await self.request("GET", "/House/houses-info", auth=True)

    async def get_house_complete_info(self, house_id: int) -> AirplastResponse:
        return await self.request("GET", "/House/house-complete-info", query={"houseId": house_id}, auth=True)

    async def rename_house(self, request: RenameHouseRequest) -> AirplastResponse:
        return await self.request("POST", "/House/rename-house", body=request, auth=True, json_body=True)

    async def set_house_timezone(self, request: SetHouseTimezoneRequest) -> AirplastResponse:
        return await self.request("POST", "/House/set-house-timezone", body=request, auth=True, json_body=True)

    async def delete_house(self, house_id: int) -> AirplastResponse:
        return await self.request("DELETE", "/House/house", query={"houseId": house_id}, auth=True)

    async def add_zone(self, request: NewZoneWithRoomsRequest) -> AirplastResponse:
        return await self.request("POST", "/House/add-zone", body=request, auth=True, json_body=True)

    async def get_user_zones(self, house_id: int) -> AirplastResponse:
        return await self.request("GET", "/House/user-zones", query={"houseId": house_id}, auth=True)

    async def delete_zone(self, zone_id: int) -> AirplastResponse:
        return await self.request("DELETE", "/House/delete-zone", query={"zoneId": zone_id}, auth=True)

    async def get_zone_devices(self, zone_id: int) -> AirplastResponse:
        return await self.request("GET", "/House/zone-devices", query={"zoneId": zone_id}, auth=True)

    async def rename_zone(self, request: RenameZoneRequest) -> AirplastResponse:
        return await self.request("POST", "/House/rename-zone", body=request, auth=True, json_body=True)

    async def get_user_rooms(self, house_id: int) -> AirplastResponse:
        return await self.request("GET", "/House/user-rooms", query={"houseId": house_id}, auth=True)

    async def get_user_free_rooms(self, house_id: int) -> AirplastResponse:
        return await self.request("GET", "/House/user-free-rooms", query={"houseId": house_id}, auth=True)

    async def add_device_room(self, request: AddNewDeviceRequest) -> AirplastResponse:
        return await self.request("POST", "/House/add-device-room", body=request, auth=True, json_body=True)

    async def rename_device(self, request: RenameDeviceRequest) -> AirplastResponse:
        return await self.request("POST", "/House/rename-device", body=request, auth=True, json_body=True)

    async def get_device_info(self, encrypted_device_info: str) -> AirplastResponse:
        return await self.request(
            "GET", "/House/device-info",
            query={"encryptedDeviceInfo": encrypted_device_info},
            auth=True,
        )

    async def get_house_config_auto(self, house_id: int, force_unique_zone: bool = False) -> AirplastResponse:
        return await self.request(
            "GET", "/House/house-config-auto",
            query={"houseId": house_id, "forceUniqueZone": force_unique_zone},
            auth=True,
        )

    # ------------------------------------------------------------------
    # Device endpoints
    # ------------------------------------------------------------------

    async def change_mode(self, request: ChangeModeRequest) -> AirplastResponse:
        return await self.request("POST", "/Device/change-mode", body=request, auth=True, json_body=True)

    async def apply_config(self, request: Any) -> AirplastResponse:
        return await self.request(
            "POST", "/Device/apply-config",
            body=request, auth=True, json_body=True,
            timeout=LONG_TIMEOUT,
        )

    async def apply_config_force_unique(self, request: Any) -> AirplastResponse:
        return await self.request(
            "POST", "/Device/apply-config-force-unique",
            body=request, auth=True, json_body=True,
            timeout=LONG_TIMEOUT,
        )

    async def get_device_status(self, device_serial_number: str) -> AirplastResponse:
        return await self.request(
            "GET", "/Device/device-status",
            query={"deviceSerialNumber": device_serial_number},
            auth=True,
        )

    async def get_house_devices_status(self, house_id: int) -> AirplastResponse:
        return await self.request(
            "GET", "/Device/house-devices-status",
            query={"houseId": house_id},
            auth=True,
        )

    async def reset_filter(self, device_serial_number: str) -> AirplastResponse:
        return await self.request(
            "GET", "/Device/reset-filter",
            query={"deviceSerialNumber": device_serial_number},
            auth=True,
        )

    async def reset_device(self, request: ResetDeviceRequest) -> AirplastResponse:
        return await self.request("POST", "/Device/reset-device", body=request, auth=True, json_body=True)

    async def send_device_config(self, device_sn: str) -> AirplastResponse:
        return await self.request(
            "GET", "/Device/send-device-config",
            query={"deviceSn": device_sn},
            auth=True,
            timeout=LONG_TIMEOUT,
        )

    # ------------------------------------------------------------------
    # Schedule endpoints
    # ------------------------------------------------------------------

    async def get_schedule(self, device_id: int) -> AirplastResponse:
        return await self.request("GET", f"/Schedule/{device_id}", auth=True)

    async def add_time_slot(self, device_id: int, time_slot: TimeSlot) -> AirplastResponse:
        return await self.request(
            "POST", f"/Schedule/{device_id}/timeslots",
            body=time_slot, auth=True, json_body=True,
        )

    async def update_time_slot(self, device_id: int, time_slot_id: int, time_slot: TimeSlot) -> AirplastResponse:
        return await self.request(
            "PUT", f"/Schedule/{device_id}/timeslots/{time_slot_id}",
            body=time_slot, auth=True, json_body=True,
        )

    async def delete_time_slot(self, device_id: int, time_slot_id: int) -> AirplastResponse:
        return await self.request("DELETE", f"/Schedule/{device_id}/timeslots/{time_slot_id}", auth=True)
