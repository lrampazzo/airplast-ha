"""Config flow tests for the Airplast integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.airplast.const import (
    CONF_BASE_URL,
    CONF_POLLING_INTERVAL,
    CONF_TOKEN,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DEFAULT_BASE_URL,
    DOMAIN,
    MIN_POLLING_INTERVAL,
)

from .conftest import MOCK_AUTH_RESPONSE, MOCK_TOKEN, MOCK_USERNAME

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_INPUT = {
    "username": MOCK_USERNAME,
    "password": "correct-password",
    "base_url": DEFAULT_BASE_URL,
}


def _mock_client_ok():
    """Patch AirplastApiClient.authenticate to return a successful response."""
    import json

    resp = MagicMock()
    resp.ok = True
    resp.status_code = 200
    resp.json = MagicMock(return_value=MOCK_AUTH_RESPONSE)
    client = MagicMock()
    client.authenticate = AsyncMock(return_value=resp)
    return client


def _mock_client_unauthorized():
    resp = MagicMock()
    resp.ok = False
    resp.status_code = 401
    resp.json = MagicMock(return_value={})
    client = MagicMock()
    client.authenticate = AsyncMock(return_value=resp)
    return client


def _mock_client_transport_error():
    from custom_components.airplast.client import AirplastRequestError

    client = MagicMock()
    client.authenticate = AsyncMock(side_effect=AirplastRequestError("connection refused"))
    return client


# ---------------------------------------------------------------------------
# Tests: initial user step
# ---------------------------------------------------------------------------


async def test_config_flow_shows_form(hass: HomeAssistant) -> None:
    """Config flow should show the user form on init."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_config_flow_success(hass: HomeAssistant) -> None:
    """Successful authentication creates a config entry."""
    with patch(
        "custom_components.airplast.config_flow.AirplastApiClient",
        return_value=_mock_client_ok(),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=_VALID_INPUT
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == MOCK_USERNAME
    data = result["data"]
    assert data[CONF_USERNAME] == MOCK_USERNAME
    assert data[CONF_TOKEN] == MOCK_TOKEN
    assert data[CONF_BASE_URL] == DEFAULT_BASE_URL
    # password must NOT be stored
    assert "password" not in data


async def test_config_flow_invalid_auth(hass: HomeAssistant) -> None:
    """401 from API shows invalid_auth error."""
    with patch(
        "custom_components.airplast.config_flow.AirplastApiClient",
        return_value=_mock_client_unauthorized(),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=_VALID_INPUT
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_auth"


async def test_config_flow_cannot_connect(hass: HomeAssistant) -> None:
    """Transport error shows cannot_connect error."""
    with patch(
        "custom_components.airplast.config_flow.AirplastApiClient",
        return_value=_mock_client_transport_error(),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=_VALID_INPUT
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "cannot_connect"


async def test_config_flow_duplicate_aborted(hass: HomeAssistant) -> None:
    """Duplicate account (same unique_id) is aborted."""
    existing = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_USERNAME,
        data={CONF_USERNAME: MOCK_USERNAME, CONF_TOKEN: MOCK_TOKEN},
    )
    existing.add_to_hass(hass)

    with patch(
        "custom_components.airplast.config_flow.AirplastApiClient",
        return_value=_mock_client_ok(),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=_VALID_INPUT
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_config_flow_username_normalised(hass: HomeAssistant) -> None:
    """Username is lowercased and stripped before storing."""
    with patch(
        "custom_components.airplast.config_flow.AirplastApiClient",
        return_value=_mock_client_ok(),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={**_VALID_INPUT, "username": "  TEST@EXAMPLE.COM  "},
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_USERNAME] == "test@example.com"


# ---------------------------------------------------------------------------
# Tests: options flow
# ---------------------------------------------------------------------------


async def test_options_flow_updates_polling_interval(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Options flow stores updated polling interval."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_POLLING_INTERVAL: 120, CONF_VERIFY_SSL: True},
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options[CONF_POLLING_INTERVAL] == 120


async def test_options_flow_enforces_minimum_polling(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Polling interval below minimum is rejected by schema validation."""
    from homeassistant.data_entry_flow import InvalidData

    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    with pytest.raises(InvalidData):
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONF_POLLING_INTERVAL: 5, CONF_VERIFY_SSL: True},
        )
