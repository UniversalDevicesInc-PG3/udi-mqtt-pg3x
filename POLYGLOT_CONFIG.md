# MQTT Plug-In for Devices

[![license][license]][localLicense]

This Plugin provides an interface between an MQTT broker and the [Polyglot PG3][poly] server.

[This thread][forum] on UDI forums has more details; ask questions there.

## MQTT Broker

If you are on PG3 or PG3X on eISY the broker is already running by default.

If you are on Polisy or running Polyglot on an RPi, see post #1 in [this thread][sonoff] on how to set up.

## Choose your setup

- **One or two simple switches** — **devlist** — [Quick start](#quick-start-one-or-two-switches-devlist)
- **Several devices, Tasmota sensors, or topic prefixes** — **devfile** — [Recommended](#recommended-yaml-devfile)
- **Already using a devfile** — edit YAML, save, run **Discover**

You must configure **devlist** and/or **devfile**. At least one is required.

## Quick start: one or two switches (devlist)

Paste into the **devlist** Custom Parameter (JSON array). A space between `[` and `{` helps some Polyglot UI editors:

```json
[  {"id": "sonoff1", "type": "switch",
        "status_topic": "stat/sonoff1/POWER",
        "cmd_topic": "cmnd/sonoff1/power"}  ]
```

Notes for basic setups:

- Switches use **stat** topics (for example `stat/sonoff1/POWER`).
- **cmd_topic** is required on every device, even sensors — use a placeholder if unused.
- After saving parameters, open the MQTT controller node and run **Discover**.

If JSON in the UI becomes awkward, switch to a **devfile** (below).

## Recommended: YAML devfile

Use a devfile when you have more than a couple of devices, any Tasmota sensors, or want shared topic prefixes (`status_prefix` / `cmd_prefix`).

Why YAML instead of a long devlist string:

- One device per block; comments allowed
- Easier to grow and back up
- Shared `~/` prefixes for many sensors on one board
- Avoids Polyglot JSON escaping issues

A starter file ships with this node server at `data/mqtt-devices.yaml`.

### Option A — Upload (no SSH)

1. Copy or edit `data/mqtt-devices.yaml` (from the node server install, or from the project repository).
2. Create a **zip** containing `mqtt-devices.yaml` at the **root** of the archive (not inside an extra folder).
3. On this Configuration page, use **Upload file**. PG3 extracts the zip into the **`data/`** folder (relative to this node server).
4. Set Custom Parameter **devfile** to:

   ```text
   data/mqtt-devices.yaml
   ```

5. Save parameters, then run **Discover** on the MQTT controller node.

To update later: edit the YAML, zip, upload again, save, **Discover**.

### Option B — SSH or your own folder

1. Place your YAML anywhere on the eISY that the node server can read.
2. Set **devfile** to the **full path** (for example `/home/admin/mqtt/mqtt-devices.yaml`).
3. Save parameters, then run **Discover**.

Relative paths (such as `data/mqtt-devices.yaml`) are resolved from this node server's install folder.

### devfile example — one Tasmota board, many sensors

```yaml
general:

- mqtt_server: "localhost"
- mqtt_port: 1884
- mqtt_user: "admin"
- mqtt_password: "admin"
- status_prefix: "tele/Wemos32"   # leading ~ on status_topic is replaced
- cmd_prefix: "cmnd/Wemos32"     # leading ~ on cmd_topic is replaced

devices:
- id: "WemosA1"
  name: "Wemos A1"
  type: "analog"
  sensor_id: "A1"
  status_topic: "~/SENSOR"
  cmd_topic: "~/POWER"
- id: "WemosT1"
  name: "Wemos T1"
  type: "Temp"
  sensor_id: "DS18B20-1"
  status_topic: "~/SENSOR"
  cmd_topic: "~/POWER"
- id: "WemosTH"
  name: "Wemos TH"
  type: "TempHumid"
  sensor_id: "AM2301"
  status_topic: "~/SENSOR"
  cmd_topic: "~/POWER"
- id: "WemosSW"
  name: "Wemos SW"
  type: "switch"
  status_topic: "~/POWER"
  cmd_topic: "~/POWER"
```

The Tasmota topic prefix (`Wemos32`) is the same for all devices on that board. **id** and **name** can differ.

### Apply changes (all setup paths)

1. Save Custom Parameters (and re-upload the devfile if you changed it on disk).
2. Open the **MQTT controller** node → run **Discover**.
3. Confirm new nodes appear and MQTT topics match your devices.

## Custom Parameters reference

```text
## REQUIRED (at least one)
devfile  - path to YAML device file (recommended: data/mqtt-devices.yaml)
devlist  - JSON array or single device object (see Quick start)

## devfile + devlist together
Load devfile first, then devlist adds devices or updates by matching id.

## MQTT broker (defaults work on eISY/PG3X)
mqtt_server   - default localhost
mqtt_port     - default 1884
mqtt_user     - default admin
mqtt_password - default admin

Precedence: Custom Parameters → devfile general section → defaults above.

## OPTIONAL topic prefixes (usually in devfile general section)
status_prefix - replaces leading ~ on status_topic only
cmd_prefix    - replaces leading ~ on cmd_topic only
```

## Device reference

### `"id":`

ISY node ID — alphanumeric and underscore only, **maximum 14 characters**.

### `"name":` (optional)

Friendly name shown on the ISY. Defaults to **id** if omitted.

### `"type":`

#### Tasmota-flashed CONTROL devices

- **switch** — Basic Sonoff or generic switch.
- **dimmer** — Wi-Fi dimmer. Use:

```text
cmd_topic: "cmnd/topic/dimmer"
status_topic: "stat/topic/DIMMER"
```

(not `.../power` and `../POWER`)

- **flag** — Condition to ISY: {OK,NOK,LO,HI,ERR,IN,OUT,UP,DOWN,TRIGGER,ON,OFF,---}
- **ifan** — [**Sonoff iFan**][ifan]; use **switch** as a separate device for the light
- **s31** — [**Sonoff S31**][s31] energy monitoring (use **switch** for outlet control)

#### Tasmota-flashed SENSOR devices

See [README — MQTT payload formats](README.md#mqtt-payload-formats) for example JSON payloads.

Add **sensor_id** — the sensor name from the Tasmota web console MQTT message:

```text
sensor_id: "sensor name"
```

- **analog** — Onboard ADC.
- **distance** — HC-SR04 ultrasonic (one sensor per device today).
- **TempHumid** — AM2301, AM2302, AM2321, DHT21, DHT22.
- **Temp** — DS18B20.
- **TempHumidPress** — BME280.

#### Non-Tasmota devices

- **RGBW** — [**RGBW strip**][RGBW strip] controller
- **sensor** — NodeMCU multi-sensor (see [forum thread][forum])
- **shellyflood** — [**Shelly Flood**][Flood]; Shelly MQTT mode, not Tasmota
- **raw** — Integer or string payload on a generic value driver
- **ratgdo** — [**ratgdo**][ratgdo] garage door; base topic for status and command
- **droplet** — [**Droplet**][Droplet] flow/volume sensor

### `"status_topic":`

- **switch** — stat topic (for example `stat/sonoff1/POWER`)
- **Tasmota sensors** — telemetry topic (for example `tele/sonoff/SENSOR`)
- **Shelly Flood** — one topic string or a list, for example:

```json
[ "shellies/shellyflood-<unique-id>/sensor/temperature",
  "shellies/shellyflood-<unique-id>/sensor/flood" ]
```

- **Droplet** — base topic; the node server subscribes to `/state` and `/health`:

```yaml
- id: "droplet_kitchen"
  type: "droplet"
  status_topic: "droplet-ABCD"
  cmd_topic: "droplet-ABCD"
```

### `"cmd_topic":`

Always required. For sensors, use any valid placeholder (for example `cmnd/sensor/power`).

## Advanced

### devlist overlay on a devfile

Keep your main config in **devfile**. Use **devlist** in Custom Parameters to add a device or replace one entry by **id** (same id overwrites the devfile entry).

### Legacy devlist single-object format

A single JSON object (not an array) still updates one device by **id**:

```json
{"id": "sonoff1", "type": "switch",
 "status_topic": "stat/sonoff1/POWER",
 "cmd_topic": "cmnd/sonoff1/power"}
```

### Troubleshooting

- **Discovery failed / file not found** — Check **devfile** path; for uploads use `data/mqtt-devices.yaml`.
- **Invalid YAML** — Validate indentation; `devices:` must be present.
- **No nodes after Discover** — Confirm at least one of **devlist** or **devfile** is set and topics match your broker.

[license]: https://img.shields.io/github/license/mashape/apistatus.svg
[localLicense]: https://github.com/Trilife/udi-mqtt-pg3x/blob/main/LICENSE
[poly]: https://github.com/Trilife/udi-mqtt-pg3x
[forum]: https://forum.universal-devices.com/forum/315-mqtt/
[sonoff]: https://forum.universal-devices.com/topic/24538-sonoff
[s31]: https://www.itead.cc/sonoff-s31.html
[ifan]: https://itead.cc/product/sonoff-ifan03-wi-fi-ceiling-fan-and-light-controller/
[RGBW strip]: http://github.com/sejgit/shelfstrip
[dimmer]: https://www.amazon.com/Dimmer-Switch-Bresuve-Wireless-Compatible/dp/B07WRJWD28?th=1
[Flood]: https://shelly-api-docs.shelly.cloud/gen1/#shelly-flood-overview
[Droplet]: https://hydrificwater.com/
[ratgdo]: https://paulwieland.github.io/ratgdo/
