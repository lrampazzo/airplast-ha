"""Opt-in live integration tests for Airplast API.

Run explicitly:
    python3 -m pytest tests/integration -m live -v
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.live


async def test_live_token_info(live_client):
    resp = await live_client.get_token_info()
    assert resp.ok, f"token-info failed: status={resp.status_code} body={resp.text}"

    payload = resp.json() or {}
    assert "username" in payload
    assert "validTo" in payload


async def test_live_refresh_token(live_client):
    resp = await live_client.refresh_token()
    assert resp.ok, f"refresh-token failed: status={resp.status_code} body={resp.text}"

    payload = resp.json() or {}
    # API may return same or new token; ensure response shape is valid.
    assert "validTo" in payload


async def test_live_get_houses(live_client):
    resp = await live_client.get_houses()
    assert resp.ok, f"houses failed: status={resp.status_code} body={resp.text}"

    payload = resp.json()
    assert isinstance(payload, list)


async def test_live_get_houses_info(live_client):
    resp = await live_client.get_houses_info()
    assert resp.ok, f"houses-info failed: status={resp.status_code} body={resp.text}"

    payload = resp.json()
    assert isinstance(payload, list)


async def test_live_feature_flags(live_client):
    resp = await live_client.get_feature_flags()
    assert resp.ok, f"feature-flags failed: status={resp.status_code} body={resp.text}"

    payload = resp.json() or {}
    assert isinstance(payload, dict)
