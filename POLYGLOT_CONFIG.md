# MQTT Plug-In for Devices

[![license][license]][localLicense]

This Plugin provides an interface between an MQTT broker and the [Polyglot PG3][poly] server.

[This thread][forum] on UDI forums has more details, ask questions there.

## MQTT Broker

If you are on PG3 or PG3X on eISY the broker is already running by default

If you are on Polisy or running Polyglot on an RPi, see post #1 in [this thread][sonoff] on how to set up.

### Custom Parameters

You will need to define the following custom parameters in Parameters OR in devfile:

```text
## ONE OF THE BELOW IS REQUIRED (see below for example of each)

You can mix and match, Parameters & devlist will add to or overwrite devfile.

devlist - JSON array, note format & space between '[' and '{'
    or
devfile - name of yaml file stored on EISY

## THESE ARE REQUIRED ONLY IF USING AN EXTERNAL SERVER OR YOU CHANGED DEFAULT SETTINGS
mqtt_server   - (default = 'localhost')
mqtt_port     - (default = 1884)
mqtt_user     - (default = admin)
mqtt_password - (default = admin)

## OPTIONAL TOPIC PREFIX PARAMS WILL REPLACE TILD ~ AT START OF TOPICS
status_prefix - (default = None)
cmd_prefix - (default = None)
```

#### `devlist example` - JSON list of devices & status/command topics note format & space between '[' and '{'

```json
[  {"id": "sonoff1", "type": "switch",
        "status_topic":  "stat/sonoff1/POWER",
        "cmd_topic":  "cmnd/sonoff1/power"},
    {"id":  "sonoff2",  "type":  "switch",
        "status_topic":  "stat/sonoff2/POWER",
        "cmd_topic":  "cmnd/sonoff2/power"}  ]
```

#### `devfile example` - YAML file stored on EISY of devices & topics

```yaml
general:

- mqtt_server: "localhost"
- mqtt_port: 1884
- mqtt_user: "admin"
- mqtt_password: "admin"
- status_prefix: "tele/Wemos32" # any status_topic starting with ~ is replaced
- cmd_prefix: "cmnd/Wemos32/power" # any cmd_topic starting with ~ is replaced

devices:
- id: "WemosA1"
  name: "Wemos A1"
  type: "analog"
  sensor_id: "A1"
  status_topic: "~/SENSOR"
  cmd_topic: "~/"
- id: "WemosR2"
  name: "Wemos AR"
  type: "analog"
  sensor_id: "Range2"
  status_topic: "~/SENSOR"
  cmd_topic: "~/"
- id: "WemosT1"
  name: "Wemos T1"
  type: "Temp"
  sensor_id: "DS18B20-1"
  status_topic: "~/SENSOR"
  cmd_topic: "~/"
- id: "WemosT2"
  name: "Wemos T2"
  type: "Temp"
  sensor_id: "DS18B20-2"
  status_topic: "~/SENSOR"
  cmd_topic: "~/"
- id: "WemosTH"
  name: "Wemos TH"
  type: "TempHumid"
  sensor_id: "AM2301"
  status_topic: "~/SENSOR"
  cmd_topic: "~/"
- id: "WemosSW"
  name: "Wemos SW"
  type: "switch"
  status_topic: "~/POWER"
  cmd_topic: "~/"
```

Note the topic (Wemos32) is the same for all sensors on the same device. The 'id' and 'name' can be different

### `"id":`

ISY node ID - Can be anything you like, but ISY restricts to alphanumeric
characters only and underline, no special characters, **maximum 14 characters**

### `"type":`

A device-type needs to be defined for by using of the following:

#### Tasmota-flashed CONTROL Devices

- **switch** - For basic sonoff or generic switch.
- **dimmer** - Smart Wi-Fi Light Dimmer Switch, [**See Amazon**][dimmer]. Use:

```text
cmd_topic: "cmnd/topic/dimmer"
status_topic: "stat/topic/DIMMER"
```

(not .../power and ../POWER)

- **flag** - For your device to send a condition to ISY {OK,NOK,LO,HI,ERR,IN,OUT,UP,DOWN,TRIGGER,ON,OFF,---}
- **ifan** - [**Sonoff iFan**][ifan] module - motor control, use **switch** as a separate device for light control
- **s31** - This is for the [**Sonoff S31**][s31] energy monitoring (use switch type for control)

#### Tasmota-flashed SENSOR Devices

If you are using 'types' in this section, you need to add this object to the configuration of the device:

```text
sensor_id: "sensor name"
```

The 'sensor name' can be found by examining an MQTT message in the Web console of the Tasmota device

- **analog** - General purpose Analog input using onboard ADC.
- **distance** - Supports HC-SR04 Ultrasonic Sensor. (Todo: Needs tweaking to work with multiple sensors)
- **TempHumid** - For AM2301, AM2302, AM2321, DHT21, DHT22 sensors.
- **Temp** - For DS18B20 sensors.
- **TempHumidPress** - Supports the BME280 sensors.

#### Non-Tasmota Devices

- **RGBW** - Control for a micro-controlled [**RGBW Strip**][RGBW strip]
- **sensor** - For nodemcu multi-sensor (see link in thread)
- **shellyflood** - [**Shelly Flood sensor**][Flood]; supports monitoring of temperature, water leak detection (`flood`), battery level, and errors. Uses Shelly's MQTT mode, not Tasmota.
- **raw** - simple str, int
- **ratgdo** - adds garage device based on the ratgdo board; use topic_prefix/device name for both status & command topics. See [**ratgdo site**](https://paulwieland.github.io/ratgdo/)
- **droplet** - [**Droplet flow/volume sensor**][Droplet] by Hydrific; monitors water flow rate and volume with cloud connectivity status. Automatically subscribes to both `/state` (JSON data) and `/health` (LWT) topics.

### `"status_topic":`

- For switch this will be the cmnd topic (like `cmnd/sonoff1/POWER`),
- For sensors this will be the telemetry topic (like `tele/sonoff/SENSOR`).
- For Shelly Floods, this will be an array, like:

```json
[ "shellies/shellyflood-<unique-id>/sensor/temperature",
   "shellies/shellyflood-<unique-id>/sensor/flood" ]
```

(they usually also have a `battery` and `error` topic that follow the same pattern).

- For Droplet devices, use the base topic (like `droplet-ABCD`), and the NodeServer will automatically subscribe to both `/state` and `/health` subtopics:

```yaml
- id: "droplet_kitchen"
  type: "droplet"
  status_topic: "droplet-ABCD"
  cmd_topic: "droplet-ABCD"  # Required but not used
```

### `"cmd_topic":`

- Is always required, even if the type doesn't support it (like a sensor)
Just enter a generic topic (`cmnd/sensor/power`).

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
