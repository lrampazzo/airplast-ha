"""Compatibility shim — re-exports async AirplastApiClient as AirplastClient.

For new code use ``airplast_client.openapi.AirplastApiClient`` directly.
"""

from .openapi import AirplastApiClient, AirplastResponse  # noqa: F401

# Alias so existing code using AirplastClient still works.
AirplastClient = AirplastApiClient

__all__ = ["AirplastClient", "AirplastApiClient", "AirplastResponse"]
