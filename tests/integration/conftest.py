"""Live integration test fixtures for Airplast API.

These tests are opt-in and require real credentials.
Resolution order for credentials:
1) Environment variables
2) .env file at repository root
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from custom_components.airplast.client import AirplastApiClient, AuthenticateRequest


def _parse_bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _read_dotenv(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data

    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            data[key] = value
    return data


@pytest.fixture(scope="session")
def live_settings() -> dict[str, str | bool]:
    root = Path(__file__).resolve().parents[2]
    dotenv = _read_dotenv(root / ".env")

    username = os.getenv("AIRPLAST_USERNAME") or dotenv.get("AIRPLAST_USERNAME")
    password = os.getenv("AIRPLAST_PASSWORD") or dotenv.get("AIRPLAST_PASSWORD")
    base_url = (
        os.getenv("AIRPLAST_BASE_URL")
        or dotenv.get("AIRPLAST_BASE_URL")
        or "https://sede.airplast.eu:4521"
    )
    verify_ssl_raw = os.getenv("AIRPLAST_VERIFY_SSL") or dotenv.get("AIRPLAST_VERIFY_SSL")
    verify_ssl = _parse_bool(verify_ssl_raw, default=True)

    if not username or not password:
        pytest.skip(
            "Live integration tests need AIRPLAST_USERNAME and AIRPLAST_PASSWORD "
            "(env vars or .env).",
            allow_module_level=True,
        )

    return {
        "username": username,
        "password": password,
        "base_url": base_url,
        "verify_ssl": verify_ssl,
    }


@pytest.fixture(scope="session")
async def live_client(live_settings):
    async with AirplastApiClient(
        base_url=str(live_settings["base_url"]),
        verify_ssl=bool(live_settings["verify_ssl"]),
    ) as client:
        auth = await client.authenticate(
            AuthenticateRequest(
                username=str(live_settings["username"]),
                password=str(live_settings["password"]),
            )
        )
        assert auth.ok, f"Authenticate failed: status={auth.status_code} body={auth.text}"
        payload = auth.json() or {}
        token = payload.get("jwtToken")
        assert token, f"No jwtToken returned: {payload}"
        client.set_token(token)
        yield client
