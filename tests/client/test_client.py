"""Tests for the async AirplastApiClient."""

from __future__ import annotations

import json
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.airplast.client import (
    AirplastApiClient,
    AirplastRequestError,
    AirplastResponse,
    AuthenticateRequest,
)
from custom_components.airplast.client.openapi import LONG_TIMEOUT


class _FakeResponse:
    def __init__(self, status: int, body):
        self.status = status
        self._body = body
        self.headers = {"Content-Type": "application/json"}
        self.url = MagicMock()
        self.url.__str__ = lambda s: "https://example.com"

    async def read(self) -> bytes:
        if isinstance(self._body, bytes):
            return self._body
        return json.dumps(self._body).encode()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass


@pytest.fixture()
def mock_session():
    return MagicMock()


@pytest.fixture()
def client(mock_session):
    return AirplastApiClient(base_url="https://example.com", session=mock_session)


@pytest.mark.asyncio
async def test_authenticate_sends_post(client, mock_session):
    fake_resp = _FakeResponse(200, {"jwtToken": "tok", "id": 1})
    mock_session.request = MagicMock(return_value=fake_resp)

    resp = await client.authenticate(AuthenticateRequest(username="u", password="p"))

    assert resp.ok
    assert resp.json()["jwtToken"] == "tok"
    mock_session.request.assert_called_once()
    call = mock_session.request.call_args
    assert call.args[0] == "POST"
    assert "/Users/authenticate" in call.args[1]


@pytest.mark.asyncio
async def test_set_token_adds_auth_header(client, mock_session):
    client.set_token("my-token")

    fake_resp = _FakeResponse(200, [])
    mock_session.request = MagicMock(return_value=fake_resp)

    await client.get_houses()

    headers = mock_session.request.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer my-token"


@pytest.mark.asyncio
async def test_token_override_header(client, mock_session):
    client.set_token("default-token")

    fake_resp = _FakeResponse(200, {})
    mock_session.request = MagicMock(return_value=fake_resp)

    await client.get_token_info(token="explicit-token")

    headers = mock_session.request.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer explicit-token"


@pytest.mark.asyncio
async def test_non_200_response_does_not_raise(client, mock_session):
    fake_resp = _FakeResponse(401, {"title": "Unauthorized"})
    mock_session.request = MagicMock(return_value=fake_resp)

    resp = await client.get_user_details()
    assert not resp.ok
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_transport_error_raises(client, mock_session):
    mock_session.request = MagicMock(
        side_effect=aiohttp.ClientConnectionError("conn refused")
    )

    with pytest.raises(AirplastRequestError):
        await client.authenticate(AuthenticateRequest(username="u", password="p"))


@pytest.mark.asyncio
async def test_timeout_error_raises(client, mock_session):
    mock_session.request = MagicMock(side_effect=TimeoutError("too slow"))

    with pytest.raises(AirplastRequestError, match="timed out"):
        await client.get_houses()


@pytest.mark.asyncio
async def test_no_session_raises():
    no_session_client = AirplastApiClient(base_url="https://example.com")
    with pytest.raises(RuntimeError, match="No aiohttp session"):
        await no_session_client.get_houses()


@pytest.mark.asyncio
async def test_query_params_drop_none(client, mock_session):
    fake_resp = _FakeResponse(200, {})
    mock_session.request = MagicMock(return_value=fake_resp)

    await client.request("GET", "/path", query={"a": 1, "b": None})

    params = mock_session.request.call_args.kwargs["params"]
    assert params == {"a": 1}


@pytest.mark.asyncio
async def test_json_body_and_extra_headers(client, mock_session):
    fake_resp = _FakeResponse(200, {})
    mock_session.request = MagicMock(return_value=fake_resp)

    await client.request(
        "POST",
        "/x",
        body={"hello": "world"},
        json_body=True,
        extra_headers={"X-Test": "yes"},
    )

    kwargs = mock_session.request.call_args.kwargs
    assert kwargs["headers"]["Content-Type"] == "application/json"
    assert kwargs["headers"]["X-Test"] == "yes"
    assert kwargs["data"] == b'{"hello":"world"}'


@dataclass
class _PayloadDC:
    a: int
    b: str | None = None


@pytest.mark.asyncio
async def test_dataclass_body_is_serialized_and_none_dropped(client, mock_session):
    fake_resp = _FakeResponse(200, {})
    mock_session.request = MagicMock(return_value=fake_resp)

    await client.request("POST", "/x", body=_PayloadDC(a=10), json_body=True)

    data = mock_session.request.call_args.kwargs["data"]
    assert data == b'{"a":10}'


@pytest.mark.asyncio
async def test_long_timeout_used_for_apply_config(client, mock_session):
    fake_resp = _FakeResponse(200, {})
    mock_session.request = MagicMock(return_value=fake_resp)

    await client.apply_config({"k": "v"})

    assert mock_session.request.call_args.kwargs["timeout"] == LONG_TIMEOUT


@pytest.mark.asyncio
async def test_owned_session_context_manager_creates_and_closes_session():
    created_session = MagicMock()
    created_session.close = AsyncMock()

    fake_resp = _FakeResponse(200, {})
    created_session.request = MagicMock(return_value=fake_resp)

    with (
        patch("custom_components.airplast.client.openapi.aiohttp.ClientSession", return_value=created_session),
        patch("custom_components.airplast.client.openapi.aiohttp.TCPConnector"),
    ):
        async with AirplastApiClient(base_url="https://example.com") as owned:
            await owned.get_houses()

    created_session.close.assert_awaited_once()


def test_airplast_response_text_json_and_repr():
    response = AirplastResponse(
        status_code=200,
        headers={"Content-Type": "application/json; charset=utf-8"},
        content=b'{"hello":"world"}',
        url="https://example.com/path",
    )

    assert response.ok is True
    assert response.text == '{"hello":"world"}'
    assert response.json() == {"hello": "world"}
    assert "status_code=200" in repr(response)


def test_airplast_response_json_none_when_empty():
    response = AirplastResponse(
        status_code=204,
        headers={"Content-Type": "application/json"},
        content=b"",
        url="https://example.com/path",
    )
    assert response.json() is None


def test_airplast_response_text_charset_fallback():
    value = "cafe".encode("latin-1")
    response = AirplastResponse(
        status_code=200,
        headers={"Content-Type": "text/plain; charset=latin-1"},
        content=value,
        url="https://example.com/path",
    )
    assert response.text == "cafe"


@pytest.mark.asyncio
async def test_verify_ssl_false_passed_to_request(mock_session):
    client = AirplastApiClient(base_url="https://example.com", session=mock_session, verify_ssl=False)
    fake_resp = _FakeResponse(200, {})
    mock_session.request = MagicMock(return_value=fake_resp)

    await client.get_houses()

    assert mock_session.request.call_args.kwargs["ssl"] is False
