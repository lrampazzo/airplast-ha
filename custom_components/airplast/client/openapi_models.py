"""Pydantic v2 models generated from openapi/airplast-openapi.json.

Run ``scripts/generate_openapi_models.py`` to regenerate.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict


class _AirplastModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
        use_enum_values=False,
    )


class _ResilientStrEnum(str, Enum):
    """Unknown API values are returned as dynamic members."""

    @classmethod
    def _missing_(cls, value: object) -> "_ResilientStrEnum":  # type: ignore[override]
        obj = str.__new__(cls, str(value))
        obj._name_ = str(value)
        obj._value_ = str(value)
        return obj


class AirQuality(_ResilientStrEnum):
    VERY_GOOD = "VeryGood"
    GOOD = "Good"
    MEDIUM = "Medium"
    POOR = "Poor"
    BAD = "Bad"


class DayOfWeek(_ResilientStrEnum):
    SUNDAY = "Sunday"
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"


class DeviceRole(_ResilientStrEnum):
    MASTER = "Master"
    SLAVE_EQUAL_MASTER = "SlaveEqualMaster"
    SLAVE_OPPOSITE_MASTER = "SlaveOppositeMaster"
    NOT_CONFIGURED = "NotConfigured"


class DeviceSubtype(_ResilientStrEnum):
    NONE_VALUE = "None"
    VERSION100 = "Version100"
    VERSION160 = "Version160"
    VERSION200 = "Version200"


class DeviceType(_ResilientStrEnum):
    GHOST = "Ghost"
    DIAMOND = "Diamond"
    ICON = "Icon"
    GEMINI = "Gemini"


class FanSpeed(_ResilientStrEnum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    NIGHT = "Night"
    TURBO = "Turbo"


class FilterStatus(_ResilientStrEnum):
    GOOD = "Good"
    MEDIUM = "Medium"
    BAD = "Bad"


class HumidityLevel(_ResilientStrEnum):
    DRY = "Dry"
    NORMAL = "Normal"
    MOIST = "Moist"


class LightSensorLevelEnum(_ResilientStrEnum):
    NOT_AVAILABLE = "NotAvailable"
    OFF = "Off"
    LOW = "Low"
    MEDIUM = "Medium"


class OperatingMode(_ResilientStrEnum):
    SMART = "Smart"
    AUTO = "Auto"
    MANUAL_HEAT_RECOVERY = "ManualHeatRecovery"
    NIGHT = "Night"
    AWAY_HOME = "AwayHome"
    SURVEILLANCE = "Surveillance"
    TIMED_EXPULSION = "TimedExpulsion"
    EXPULSION = "Expulsion"
    INTAKE = "Intake"
    MASTER_SLAVE_FLOW = "MasterSlaveFlow"
    SLAVE_MASTER_FLOW = "SlaveMasterFlow"
    OFF = "Off"


class PacketType(_ResilientStrEnum):
    CONNECTION = "Connection"
    STATUS = "Status"
    COMMAND = "Command"
    FW_VERSIONS = "FwVersions"
    OUTSIDE_WEATHER_REQUEST = "OutsideWeatherRequest"
    UNKNOWN = "Unknown"


class ResetType(_ResilientStrEnum):
    CONNECTION_RESET = "ConnectionReset"
    DEVICE_RESET = "DeviceReset"


class RoomNames(_ResilientStrEnum):
    KITCHEN = "Kitchen"
    LIVING_ROOM = "LivingRoom"
    BEDROOM = "Bedroom"
    BATHROOM = "Bathroom"
    DINNING_ROOM = "DinningRoom"
    CHILDREN_ROOM = "ChildrenRoom"
    BATHROOM2 = "Bathroom2"
    BATHROOM3 = "Bathroom3"
    BEDROOM2 = "Bedroom2"
    BEDROOM3 = "Bedroom3"
    BEDROOM4 = "Bedroom4"
    STUDY = "Study"
    LAUNDRY = "Laundry"
    GARAGE = "Garage"
    BASEMENT = "Basement"
    ATTIC = "Attic"
    GENERIC_ROOM1 = "GenericRoom1"
    GENERIC_ROOM2 = "GenericRoom2"


class ScheduleState(_ResilientStrEnum):
    NOT_AVAILABLE = "NotAvailable"
    OFF = "Off"
    ON = "On"


class UserOperationType(_ResilientStrEnum):
    CONFIRM_ACCOUNT = "ConfirmAccount"
    RECOVER_PASSWORD = "RecoverPassword"
    CHANGE_USERNAME = "ChangeUsername"


# ---------------------------------------------------------------------------
# Object models
# ---------------------------------------------------------------------------

class AddHouseRequest(_AirplastModel):
    name: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[int] = None

class AddNewDeviceRequest(_AirplastModel):
    deviceName: str
    encryptedDeviceInfo: str
    roomName: RoomNames
    houseId: int

class AuthenticateRequest(_AirplastModel):
    username: str
    password: Optional[str] = None

class AuthenticateResponse(_AirplastModel):
    id: Optional[int] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    completeName: Optional[str] = None
    username: Optional[str] = None
    jwtToken: Optional[str] = None
    expiresAt: Optional[datetime] = None
    userLevel: Optional[int] = None

class ChangeModeRequest(_AirplastModel):
    deviceSerialNumber: Optional[str] = None
    operatingMode: Optional[OperatingMode] = None
    fanSpeed: Optional[FanSpeed] = None
    humidityLevel: Optional[HumidityLevel] = None
    lightSensorLevel: Optional[LightSensorLevelEnum] = None
    isScheduleMode: Optional[bool] = None

class ChangeUsernameRequest(_AirplastModel):
    password: Optional[str] = None
    newUsername: Optional[str] = None

class ConfirmRegisterRequest(_AirplastModel):
    username: str
    shortToken: str

class Device(_AirplastModel):
    id: Optional[int] = None
    deviceType: Optional[DeviceType] = None
    deviceSubtype: Optional[DeviceSubtype] = None
    serialNumber: str
    userId: Optional[int] = None
    name: str
    role: Optional[DeviceRole] = None
    zoneIndex: Optional[int] = None
    installation: Optional[datetime] = None
    radioFwVersion: Optional[str] = None
    microFwVersion: Optional[str] = None
    radioAtCommandsFwVersion: Optional[str] = None
    roomId: Optional[int] = None

class FeatureFlagsResponse(_AirplastModel):
    rememberMeLogin: Optional[bool] = None
    resetDeviceEndpoint: Optional[bool] = None
    weeklyScheduler: Optional[bool] = None
    improvedRoomList: Optional[bool] = None
    turboMode: Optional[bool] = None

class GeminiDeviceInfo(_AirplastModel):
    device: Optional[Device] = None
    statusPacket: Optional[StatusPacket] = None

class House(_AirplastModel):
    userId: Optional[int] = None
    id: Optional[int] = None
    name: str
    zones: Optional[List[Zone]] = None
    rooms: Optional[List[Room]] = None
    schedule: Optional[Schedule] = None
    hasZones: Optional[bool] = None
    hasDevices: Optional[bool] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[int] = None
    ianaTimezone: Optional[str] = None
    currentHouseTime: Optional[datetime] = None

class HouseDevicesInfo(_AirplastModel):
    zoneDevicesInfo: Optional[List[ZoneDeviceInfo]] = None
    uniqueZoneStatusPacket: Optional[StatusPacket] = None
    uniqueZoneDevicesCount: Optional[int] = None
    masterSn: Optional[str] = None
    geminiDevicesInfo: Optional[List[GeminiDeviceInfo]] = None

class HouseInfo(_AirplastModel):
    houseId: Optional[int] = None
    houseName: Optional[str] = None
    houseZonesCount: Optional[int] = None
    houseDevicesCount: Optional[int] = None
    nonGeminiZones: Optional[List[Zone]] = None
    nonGeminiDevices: Optional[List[Device]] = None
    roomsWithGeminiDevices: Optional[List[Room]] = None
    geminiDevices: Optional[List[Device]] = None

class NewOperationTokenRequest(_AirplastModel):
    email: Optional[str] = None
    userOperationType: Optional[UserOperationType] = None

class NewZoneWithRoomsRequest(_AirplastModel):
    zoneName: Optional[str] = None
    houseId: Optional[int] = None
    roomsId: Optional[List[int]] = None

class ProblemDetails(_AirplastModel):
    type: Optional[str] = None
    title: Optional[str] = None
    status: Optional[int] = None
    detail: Optional[str] = None
    instance: Optional[str] = None

class RecoverPasswordRequest(_AirplastModel):
    username: Optional[str] = None
    shortToken: Optional[str] = None
    newPassword: Optional[str] = None

class RegisterRequestWs(_AirplastModel):
    firstName: str
    lastName: str
    username: str
    password: str
    level: Optional[int] = None
    privacyPolicyConsent: bool
    legalNotesContent: bool
    marketingConsent: bool

class RenameDeviceRequest(_AirplastModel):
    deviceId: Optional[int] = None
    newName: Optional[str] = None

class RenameHouseRequest(_AirplastModel):
    houseId: Optional[int] = None
    newName: Optional[str] = None

class RenameZoneRequest(_AirplastModel):
    zoneId: Optional[int] = None
    newName: Optional[str] = None

class ResetDeviceRequest(_AirplastModel):
    deviceSerialNumber: Optional[str] = None
    resetType: Optional[ResetType] = None

class Room(_AirplastModel):
    id: Optional[int] = None
    name: RoomNames
    houseId: Optional[int] = None
    userId: Optional[int] = None
    devices: Optional[List[Device]] = None
    roomDevicesCount: Optional[int] = None

class Schedule(_AirplastModel):
    id: Optional[int] = None
    zoneId: Optional[int] = None
    houseId: Optional[int] = None
    deviceId: Optional[int] = None
    timeSlots: Optional[List[TimeSlot]] = None

class SetHouseTimezoneRequest(_AirplastModel):
    houseId: Optional[int] = None
    timezone: Optional[int] = None

class StatusPacket(_AirplastModel):
    packetType: Optional[PacketType] = None
    deviceType: Optional[DeviceType] = None
    deviceSubtype: Optional[DeviceSubtype] = None
    deviceSerialNumber: Optional[str] = None
    operatingMode: Optional[OperatingMode] = None
    fanSpeed: Optional[FanSpeed] = None
    humidityLevel: Optional[HumidityLevel] = None
    temperature: Optional[int] = None
    humidity: Optional[int] = None
    airQuality: Optional[AirQuality] = None
    humidityAlarm: Optional[bool] = None
    filtersStatus: Optional[FilterStatus] = None
    nightAlarm: Optional[bool] = None
    deviceRole: Optional[DeviceRole] = None
    lastOperatingMode: Optional[OperatingMode] = None
    lightSensorLevel: Optional[LightSensorLevelEnum] = None
    signalStrenght: Optional[int] = None
    isScheduled: Optional[ScheduleState] = None
    isTurboAvailable: Optional[bool] = None

class TimeSlot(_AirplastModel):
    id: Optional[int] = None
    dayOfWeek: Optional[DayOfWeek] = None
    startTime: Optional[str] = None
    endTime: Optional[str] = None
    operatingMode: Optional[OperatingMode] = None
    fanSpeed: Optional[FanSpeed] = None
    humidityLevel: Optional[HumidityLevel] = None
    lightSensorLevel: Optional[LightSensorLevelEnum] = None
    scheduleId: Optional[int] = None

class TimeSlotModificationResult(_AirplastModel):
    modifiedTimeSlot: Optional[TimeSlot] = None
    activeTimeSlot: Optional[TimeSlot] = None

class TokenInfoResponse(_AirplastModel):
    userId: Optional[int] = None
    validFrom: Optional[datetime] = None
    validTo: Optional[datetime] = None
    username: Optional[str] = None

class TokenRefreshResponse(_AirplastModel):
    userId: Optional[int] = None
    validFrom: Optional[datetime] = None
    validTo: Optional[datetime] = None
    token: Optional[str] = None
    username: Optional[str] = None

class UpdateFirstLastNameRequest(_AirplastModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None

class UpdatePasswordRequest(_AirplastModel):
    oldPassword: Optional[str] = None
    newPassword: Optional[str] = None

class UserDetailsResponse(_AirplastModel):
    id: Optional[int] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    username: Optional[str] = None
    userSince: Optional[datetime] = None

class Zone(_AirplastModel):
    id: Optional[int] = None
    name: str
    houseId: Optional[int] = None
    rooms: Optional[List[Room]] = None
    schedule: Optional[Schedule] = None

class ZoneDeviceInfo(_AirplastModel):
    zone: Optional[Zone] = None
    statusPacket: Optional[StatusPacket] = None
    zoneDevicesCount: Optional[int] = None
    masterSn: Optional[str] = None


# Backwards-compatibility aliases
LoginRequest = AuthenticateRequest
ChangeEmailRequest = ChangeUsernameRequest
ChangePasswordRequest = UpdatePasswordRequest
CompleteRegistrationRequest = ConfirmRegisterRequest
CompleteRecoverPasswordRequest = RecoverPasswordRequest
UpdateUserDetailsRequest = UpdateFirstLastNameRequest
AddZoneRequest = NewZoneWithRoomsRequest
LightSensorLevel = LightSensorLevelEnum
