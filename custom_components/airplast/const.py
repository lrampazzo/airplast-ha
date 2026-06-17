"""Constants for the Airplast Home Assistant integration."""

from __future__ import annotations

from .client import FanSpeed, OperatingMode

DOMAIN = "airplast"
PLATFORMS = ["sensor", "binary_sensor", "select", "button"]

# Config / options entry keys
CONF_USERNAME = "username"
CONF_BASE_URL = "base_url"
CONF_TOKEN = "token"
CONF_TOKEN_EXPIRY = "token_expiry"
CONF_POLLING_INTERVAL = "polling_interval"
CONF_VERIFY_SSL = "verify_ssl"

# Defaults
DEFAULT_BASE_URL = "https://sede.airplast.eu:4521"
DEFAULT_POLLING_INTERVAL = 60  # seconds
MIN_POLLING_INTERVAL = 30  # seconds

# Coordinator data keys
DATA_COORDINATOR = "coordinator"
DATA_CLIENT = "client"

# OperatingMode → human-readable preset name (for fan entity)
OPERATING_MODE_LABELS: dict[str, str] = {
    OperatingMode.SMART: "Smart",
    OperatingMode.AUTO: "Auto",
    OperatingMode.MANUAL_HEAT_RECOVERY: "Manual Heat Recovery",
    OperatingMode.NIGHT: "Night",
    OperatingMode.AWAY_HOME: "Away / Home",
    OperatingMode.SURVEILLANCE: "Surveillance",
    OperatingMode.TIMED_EXPULSION: "Timed Expulsion",
    OperatingMode.EXPULSION: "Expulsion",
    OperatingMode.INTAKE: "Intake",
    OperatingMode.MASTER_SLAVE_FLOW: "Master → Slave Flow",
    OperatingMode.SLAVE_MASTER_FLOW: "Slave → Master Flow",
    OperatingMode.OFF: "Off",
}

# Label → OperatingMode (reverse map, built at import time)
LABEL_TO_OPERATING_MODE: dict[str, OperatingMode] = {
    v: k for k, v in OPERATING_MODE_LABELS.items()  # type: ignore[misc]
}

# FanSpeed ordered levels used for percentage mapping when confirmed linear
FAN_SPEED_ORDERED = [FanSpeed.LOW, FanSpeed.MEDIUM, FanSpeed.HIGH]
