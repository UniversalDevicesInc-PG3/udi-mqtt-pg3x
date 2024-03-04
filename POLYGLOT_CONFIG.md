# MQTT Nodeserver for Devices

[![license]][localLicense]

This Poly provides an interface between MQTT broker and [Polyglot PG3][poly] server.

[This thread][forum] on UDI forums has more details, ask questions there.

## MQTT Broker

You will need a MQTT broker running (can be on RPi running Polyglot) \
 (Likely already running, if you are on PG3 or PG3x on eISY) \
 See post #1 in [this thread][sonoff] on how to setup.

### Custom Parameters

You will need to define the following custom parameters:

#### `mqtt_server`  - (default = 'localhost')

#### `mqtt_port` -  (default = 1884) :do not change, if using MQTT on PG3x

#### `mqtt_user` - (default = admin) :not required if using MQTT on EISY/Polisy

#### `mqtt_password` - (default = admin) :not required for PG3x

#### `devfile` - yaml file of devices, status & command topics

PREFERRED METHOD and alternative to `devlist` option below \
Use the yaml file instead, start with `devices:` and then same syntax

#### `devlist` - JSON list of devices, status & command topics

for example: \
`[  {"id":  "sonoff1",  "type":  "switch",  "status_topic":  "stat/sonoff1/POWER", "cmd_topic":  "cmnd/sonoff1/power"},  {"id":  "sonoff2",  "type":  "switch", "status_topic":  "stat/sonoff2/POWER",  "cmd_topic":  "cmnd/sonoff2/power"}  ]`

##### `"id":`

ISY node ID - Can be anything you like, but ISY restricts to alphanumeric \
characters only and underline, no special characters, maximum 14 characters

##### `"type":`

One of the following:

- *switch* - For basic sonoff or generic switch.
- *sensor* - For nodemcu multi-sensor (see link in thread).
- *flag* - For your device to send a condition to ISY {OK,NOK,LO,HI,ERR,IN,OUT,UP,DOWN,TRIGGER,ON,OFF,---}
- *TempHumid* - For AM2301, AM2302, AM2321, DHT21, DHT22 sensors. * see details below
- *Temp* - For DS18B20 sensors. * see details below
- *TempHumidPress* - Supports the BME280 sensors.
- *distance* - Supports HC-SR04 Ultrasonic Sensor.
- *analog* - General purpose Analog input using onboard ADC. * see details below
- *s31* - This is for the [Sonoff S31][s31] energy monitoring \
(use switch type for control)
- *RGBW* - Control for a micro-controlled [RGBW strip]
- *ifan* - Sonoff [iFan] module - motor control, \
use *switch* as a separate device for light control
- *shellyflood* - [Shelly Flood sensor][Flood]; supports monitoring of \
temperature, water leak detection (`flood`), battery level, and errors.
- *dimmer* - Smart Wi-Fi Light Dimmer Switch, [**See Amazon**][dimmer] \
Important, use \
cmd_topic: cmnd/topic/dimmer \
status_topic: stat/topic/DIMMER (not .../power and ../POWER)
- *ratgdo* - adds garage device based on the ratgdo board. \
use topic_prefix/device name for both status & command topics \
see [**ratgdo site**](https://paulwieland.github.io/ratgdo/)

##### `"status_topic":`

- For switch this will be the cmnd topic (like `cmnd/sonoff1/power`), \
but on sensors this will be the telemetry topic (like `tele/sonoff/SENSOR`). \
For Shelly Floods, this will be an array, like \
`[ "shellies/shellyflood-<unique-id>/sensor/temperature", "shellies/shellyflood-<unique-id>/sensor/flood" ]` \
(they usually also have a `battery` and `error` topic that follow the same pattern).

##### `"cmd_topic":`

- Is always required, even if the type doesn't support it (like a sensor) \
Just enter a generic topic (`cmnd/sensor/POWER`). \
  - if you are using ANALOG, TEMP or TEMPHUMID 'types', you need to add \
    a <'sensor_id': 'sensor name'> object to the configuration of the device \
  - the 'sensor name' can be found by examining an mqtt message in the Web \
  console of the Tasmota device

##### a devfile for those sensors

devices:

- id: "WemosA1"
  name: "Wemos A1"
  type: "analog"
  sensor_id: "A1"
  status_topic: "tele/Wemos32/SENSOR"
  cmd_topic: "cmnd/Wemos32/POWER"
- id: "WemosR2"
  name: "Wemos AR"
  type: "analog"
  sensor_id: "Range2"
  status_topic: "tele/Wemos32/SENSOR"
  cmd_topic: "cmnd/Wemos32/POWER"
- id: "WemosT1"
  name: "Wemos T1"
  type: "Temp"
  sensor_id: "DS18B20-1"
  status_topic: "tele/Wemos32/SENSOR"
  cmd_topic: "cmnd/Wemos32/POWER"
- id: "WemosT2"
  name: "Wemos T2"
  type: "Temp"
  sensor_id: "DS18B20-2"
  status_topic: "tele/Wemos32/SENSOR"
  cmd_topic: "cmnd/Wemos32/POWER"
- id: "WemosTH"
  name: "Wemos TH"
  type: "TempHumid"
  sensor_id: "AM2301"
  status_topic: "tele/Wemos32/SENSOR"
  cmd_topic: "cmnd/Wemos32/POWER"
- id: "WemosSW"
  name: "Wemos SW"
  type: "switch"
  status_topic: "stat/Wemos32/POWER"
  cmd_topic: "cmnd/Wemos32/power"

- ** Note the topic (Wemos32) is the same for all sensors on the same device \
The 'id' and 'name' can be different

[license]: https://img.shields.io/github/license/mashape/apistatus.svg
[localLicense]: https://github.com/Trilife/udi-mqtt-pg3x/blob/main/LICENSE
[poly]: https://github.com/UniversalDevicesInc/pg3-dist
[forum]: https://forum.universal-devices.com/topic/24538-sonoff/?tab=comments#comment-244571
[sonoff]: https://forum.universal-devices.com/topic/24538-sonoff
[s31]: https://www.itead.cc/sonoff-s31.html
[ifan]: https://itead.cc/product/sonoff-ifan03-wi-fi-ceiling-fan-and-light-controller/
[RGBW strip]: http://github.com/sejgit/shelfstrip
[dimmer]: https://www.amazon.com/Dimmer-Switch-Bresuve-Wireless-Compatible/dp/B07WRJWD28?th=1
[Flood]: https://shelly-api-docs.shelly.cloud/gen1/#shelly-flood-overview
