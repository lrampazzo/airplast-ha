"""Request models for the Airplast backend."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Mapping


JsonLike = Mapping[str, Any] | list[Any] | str | int | float | bool | None


def to_payload(value: Any) -> Any:
    """Convert dataclasses and enums into JSON-serializable payloads."""
    if is_dataclass(value):
        return _drop_none(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {key: to_payload(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [to_payload(item) for item in value]
    return value


def _drop_none(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _drop_none(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [_drop_none(item) for item in value]
    return value


@dataclass(slots=True)
class LoginRequest:
    username: str
    password: str


@dataclass(slots=True)
class CompleteRecoverPasswordRequest:
    username: str | None = None
    shortToken: str | None = None
    newPassword: str | None = None


@dataclass(slots=True)
class RegisterRequest:
    firstName: str
    lastName: str
    username: str
    password: str
    privacyPolicyConsent: bool
    legalNotesContent: bool
    marketingConsent: bool
    level: int | None = None


@dataclass(slots=True)
class CompleteRegistrationRequest:
    username: str
    shortToken: str


@dataclass(slots=True)
class UpdateUserDetailsRequest:
    firstName: str | None = None
    lastName: str | None = None


@dataclass(slots=True)
class ChangePasswordRequest:
    oldPassword: str | None = None
    newPassword: str | None = None


@dataclass(slots=True)
class ChangeEmailRequest:
    password: str | None = None
    newUsername: str | None = None


@dataclass(slots=True)
class CompleteChangeEmailRequest:
    shortToken: str


@dataclass(slots=True)
class RequestNewOperationTokenRequest:
    email: str | None = None
    userOperationType: int | str | None = None


@dataclass(slots=True)
class AddHouseRequest:
    name: str
    address: str
    latitude: float
    longitude: float
    timezone: int


@dataclass(slots=True)
class SetHouseTimezoneRequest:
    houseId: int
    timezone: int


@dataclass(slots=True)
class AddNewDeviceRequest:
    deviceName: str
    encryptedDeviceInfo: str
    roomName: int | str
    houseId: int


@dataclass(slots=True)
class AddZoneRequest:
    zoneName: str
    houseId: int
    roomsId: list[int]


@dataclass(slots=True)
class RenameHouseRequest:
    houseId: int
    newName: str


@dataclass(slots=True)
class RenameZoneRequest:
    zoneId: int
    newName: str


@dataclass(slots=True)
class RenameDeviceRequest:
    deviceId: int
    newName: str


@dataclass(slots=True)
class ChangeWorkingModeRequest:
    deviceSerialNumber: str | None = None
    operatingMode: int | str | None = None
    fanSpeed: int | str | None = None
    humidityLevel: int | str | None = None
    lightSensorLevel: int | str | None = None
    isScheduleMode: bool | None = None


@dataclass(slots=True)
class ResetDeviceRequest:
    deviceSerialNumber: str | None = None
    resetType: int | str | None = None


@dataclass(slots=True)
class TimeSlot:
    id: int | None = None
    dayOfWeek: int | str | None = None
    startTime: str | None = None
    endTime: str | None = None
    operatingMode: int | str | None = None
    fanSpeed: int | str | None = None
    humidityLevel: int | str | None = None
    lightSensorLevel: int | str | None = None
    scheduleId: int | None = None