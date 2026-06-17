"""Tests for Pydantic v2 OpenAPI models."""

from __future__ import annotations

import pytest

from custom_components.airplast.client.openapi_models import (
    AuthenticateRequest,
    AuthenticateResponse,
    ChangeModeRequest,
    FanSpeed,
    HouseDevicesInfo,
    OperatingMode,
    StatusPacket,
)


def test_authenticate_request_serialises():
    req = AuthenticateRequest(username="user@example.com", password="secret")
    payload = req.model_dump(exclude_none=True)
    assert payload == {"username": "user@example.com", "password": "secret"}


def test_authenticate_request_no_password():
    req = AuthenticateRequest(username="u")
    payload = req.model_dump(exclude_none=True)
    assert "password" not in payload


def test_authenticate_response_parses():
    raw = {
        "id": 42,
        "username": "u@example.com",
        "jwtToken": "tok",
        "expiresAt": "2030-01-01T00:00:00Z",
        "userLevel": 1,
    }
    resp = AuthenticateResponse.model_validate(raw)
    assert resp.jwtToken == "tok"
    assert resp.id == 42


def test_status_packet_parses_enums():
    raw = {
        "operatingMode": "Smart",
        "fanSpeed": "High",
        "temperature": 22,
        "humidity": 55,
    }
    packet = StatusPacket.model_validate(raw)
    assert packet.operatingMode == OperatingMode.SMART
    assert packet.fanSpeed == FanSpeed.HIGH
    assert packet.temperature == 22


def test_resilient_enum_unknown_value():
    """Unknown enum values should not raise – they become dynamic members."""
    mode = OperatingMode._missing_("FutureMode")
    assert mode.value == "FutureMode"
    # str(enum_member) returns "ClassName.MemberName"; use .value for the raw string
    assert mode.value == "FutureMode"


def test_change_mode_request_excludes_none():
    req = ChangeModeRequest(deviceSerialNumber="SN123", operatingMode=OperatingMode.AUTO)
    payload = req.model_dump(exclude_none=True)
    assert "fanSpeed" not in payload
    assert payload["operatingMode"] == OperatingMode.AUTO


def test_house_devices_info_empty():
    info = HouseDevicesInfo.model_validate({})
    assert info.zoneDevicesInfo is None
    assert info.geminiDevicesInfo is None
