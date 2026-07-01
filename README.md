# Airplast for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Control and monitor your **Airplast ventilation units** from [Home Assistant](https://www.home-assistant.io/).  
The integration communicates with the Airplast AirApp cloud backend — the same API used by the official mobile app.

---

## Features

- **Sensors** — temperature, humidity, air quality, operating mode, fan speed, humidity level, filter status, signal strength, schedule state
- **Binary sensors** — humidity alarm, twilight sensor (day/night detection), turbo availability
- **Fan controls** — turn on/off and switch between all Airplast operating modes (Smart, Auto, Night, Away/Home, Surveillance, Expulsion, Intake, …)
- **Cloud polling** — configurable interval (default 60 s, minimum 30 s)
- **Config flow** — set up entirely from the Home Assistant UI, no YAML required
- **Reauth flow** — automatic token refresh; prompts for re-login only when necessary
- **Diagnostics** — redacted diagnostic data available for troubleshooting

### Not included in v1

BLE provisioning, device-local TCP, schedule editing, filter/device reset, and house/zone management.

---

## Requirements

- Home Assistant 2024.1 or later
- An active [Airplast AirApp](https://www.airplast.eu) account with at least one configured device

---

## Installation via HACS

1. Open HACS in your Home Assistant instance.
2. Go to **Integrations → ⋮ → Custom repositories**.
3. Add this repository URL and select category **Integration**.
4. Search for **Airplast** and click **Download**.
5. Restart Home Assistant.

---

## Manual installation

```bash
git clone https://github.com/lrampazzo/airplast-ha.git
cp -r airplast-ha/custom_components/airplast <ha-config>/custom_components/airplast
# restart Home Assistant
```

---

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Airplast** and select it.
3. Enter your Airplast account **username** (email) and **password**.
4. Optionally override the backend URL (leave blank for the default `https://sede.airplast.eu:4521`).
5. Click **Submit** — the integration authenticates, discovers your houses and devices, and creates entities automatically.

### Options

After setup, open the integration entry and click **Configure**:

| Option | Default | Minimum |
|---|---|---|
| Polling interval (seconds) | 60 | 30 |
| Verify TLS certificate | Enabled | — |

> Disable TLS verification only in development environments.

---

## Entities

Each Airplast device appears as a single HA device entry identified by its serial number.

### Sensors

| Entity | Device class | Unit / Values |
|---|---|---|
| Temperature | `temperature` | °C |
| Humidity | `humidity` | % |
| Air Quality | — | `VeryGood` / `Good` / `Medium` / `Poor` / `Bad` |
| Operating Mode | — | string |
| Fan Speed | — | `Low` / `Medium` / `High` / `Night` / `Turbo` |
| Humidity Level | — | `Dry` / `Normal` / `Moist` |
| Filter Status | — | `Good` / `Medium` / `Bad` |
| Signal Strength | `signal_strength` | dBm |
| Schedule State | — | `NotAvailable` / `Off` / `On` |

### Binary Sensors

| Entity | Device class |
|---|---|
| Humidity Alarm | `moisture` |
| Twilight Sensor | — |
| Turbo Available | — |

### Fan

Each controllable device exposes a fan entity with the following preset modes:

`Smart` · `Auto` · `Manual Heat Recovery` · `Night` · `Away / Home` · `Surveillance` · `Timed Expulsion` · `Expulsion` · `Intake` · `Master → Slave Flow` · `Slave → Master Flow` · `Off`

---

## Development

```bash
# install dependencies (aiohttp, pydantic v2, pytest)
pip install -e ".[dev]"

# validate compilation
python3 -m compileall custom_components

# regenerate models after a spec update
python3 openapi/generate_models.py
```

Copy `.env.example` to `.env` and fill in your credentials for manual testing — this file is gitignored:

```bash
cp .env.example .env
```

## Testing

The test suite has two layers:

1. Unit/integration-mocked tests (`tests/client`, `tests/custom_components`) for deterministic CI-safe coverage.
2. Live API tests (`tests/integration`) that call the real Airplast backend and require credentials.

### Run all default tests

```bash
python3 -m pytest tests/ -v --tb=short
```

### Run only client tests

```bash
python3 -m pytest tests/client -v
```

### Run only Home Assistant integration tests

```bash
python3 -m pytest tests/custom_components/airplast -v
```

### Run live tests against real Airplast APIs

Live tests are marked with `live` and are opt-in.

```bash
python3 -m pytest tests/integration -m live -v --tb=short
```

Credentials are loaded in this order:

1. Environment variables
2. `.env` file in repository root

Supported variables:

- `AIRPLAST_USERNAME`
- `AIRPLAST_PASSWORD`
- `AIRPLAST_BASE_URL` (optional, defaults to `https://sede.airplast.eu:4521`)
- `AIRPLAST_VERIFY_SSL` (optional, `true`/`false`, defaults to `true`)

If credentials are missing, live tests are skipped automatically.

---

## Contributing

Pull requests are welcome. Please open an issue first for significant changes.

---

## License

Proprietary — all rights reserved.
