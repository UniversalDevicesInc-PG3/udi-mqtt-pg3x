# UDI Polyglot PG3x MQTT Poly

[![license][license]][localLicense]

This Polyglot node server connects an MQTT broker to the ISY via Polyglot v3 (PG3x).

## Installation

Install from the Polyglot store. After install, open this node server's **Configuration** page for setup instructions.

For a few devices you can use inline JSON; for larger installs the node server supports an external YAML device file in its `data/` folder.

## Supported devices

**Tasmota control:** switches, dimmers, fans (iFan), flags, Sonoff S31 energy monitoring

**Tasmota sensors:** DHT temp/humidity, DS18B20 temp, BME280, analog, HC-SR04 distance

**Other:** RGBW strips, Shelly Flood, ratgdo garage doors, Droplet flow/volume sensors, generic raw and multi-sensor nodes

## MQTT payload formats

These are the JSON shapes each sensor node expects on its `status_topic`. The Controller unwraps Tasmota `StatusSNS` envelopes before routing messages to nodes, so raw Tasmota telemetry works as-is.

For Tasmota sensors, set `sensor_id` in device configuration to the top-level key shown below (the sensor name from the Tasmota web console / `tele/.../SENSOR` message). If omitted, the default key is `SINGLE_SENSOR`.

| Config type | JSON key | Fields |
|-------------|----------|--------|
| **TempHumid** | `sensor_id` (e.g. `AM2301`, `DHT22`) | `Temperature`, `Humidity`, `DewPoint` |
| **Temp** | `sensor_id` or `DS18B20` | `Temperature` |
| **TempHumidPress** | `sensor_id` (e.g. `BME280`) | `Temperature`, `Humidity`, `DewPoint`, `Pressure` |
| **analog** | `ANALOG` → channel (e.g. `A0`) | numeric ADC value |
| **distance** | `SR04` | `Distance` (cm) |
| **s31** | `ENERGY` | `Current`, `Power`, `Voltage`, `Factor`, `Total` |
| **sensor** | (flat object) | `motion`, `temperature`, `humidity`, `heatIndex`, `ldr`, `state`, `brightness`, `color` |
| **droplet** | (flat object on `…/state`) | `server`, `signal`, `flow`, `volume` |

**TempHumid** (AM2301, DHT22, etc.):

```json
{
  "AM2301": {
    "Temperature": 72.5,
    "Humidity": 55.0,
    "DewPoint": 54.3
  }
}
```

**Temp** (DS18B20):

```json
{
  "DS18B20": {
    "Temperature": 72.5
  }
}
```

**TempHumidPress** (BME280):

```json
{
  "BME280": {
    "Temperature": 72.5,
    "Humidity": 45.0,
    "DewPoint": 50.2,
    "Pressure": 1013.25
  }
}
```

**analog**:

```json
{
  "ANALOG": {
    "A0": 512
  }
}
```

**distance** (HC-SR04):

```json
{
  "SR04": {
    "Distance": 50
  }
}
```

**s31** (Sonoff S31 energy):

```json
{
  "ENERGY": {
    "Current": 1.5,
    "Power": 180.0,
    "Voltage": 120.0,
    "Factor": 0.95,
    "Total": 12.5
  }
}
```

**sensor** (NodeMCU multi-sensor):

```json
{
  "motion": "active",
  "temperature": 72.0,
  "humidity": 55,
  "heatIndex": 73.5,
  "ldr": 750,
  "state": "ON",
  "brightness": 200,
  "color": { "r": 255, "g": 128, "b": 64 }
}
```

**droplet** (on `{base_topic}/state`; health uses plain text `online` or `offline` on `{base_topic}/health`):

```json
{
  "server": "Connected",
  "signal": "Strong Signal",
  "flow": 0.1,
  "volume": 0.2
}
```

**shellyflood** and **raw** do not use JSON — Shelly Flood publishes a single value per topic (e.g. `true` on `…/sensor/flood`), and **raw** expects a plain integer string (e.g. `42`).

## Help

Questions and support: [UDI MQTT forum][forum]

[license]: https://img.shields.io/github/license/mashape/apistatus.svg
[localLicense]: https://github.com/Trilife/udi-mqtt-pg3x/blob/main/LICENSE
[forum]: https://forum.universal-devices.com/forum/315-mqtt/
