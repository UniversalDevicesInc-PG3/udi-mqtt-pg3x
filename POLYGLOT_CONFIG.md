# MQTT Nodeserver for Devices

[![license][license]][localLicense]

This Poly provides an interface between MQTT broker and the [Polyglot PG3][poly] server.

[This thread][forum] on UDI forums has more details, ask questions there.

## MQTT Broker
If you are on PG3 or PG3X on eISY the broker is already running by default 
 
IF you are on Polisy or running Polyglot on an RPi, see post #1 in [this thread][sonoff] on how to setup.

### Custom Parameters

You will need to define the following custom parameters:  
mqtt server, port, user, & password are only required if using an external  
mqtt server you set up

```json
# ONLY REQUIRED IF EXTERNAL SERVER OR YOU CHANGED LOCAL SETTINGS
mqtt_server   - (default = 'localhost')

mqtt_port     -  (default = 1884)

mqtt_user     - (default = admin)

mqtt_password - (default = admin)

# ONE OF BELOW IS REQUIRED (see below for example of each)
devfile - name of yaml file stored on EISY
or
devlist - JSON array, note format & space between '[' and '{'
```

#### `devlist example` - JSON list of devices & status/command topics

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
devices:

- id: "WemosA1"
  name: "Wemos A1"
  type: "analog"
  sensor_id: "A1"
  status_topic: "tele/Wemos32/SENSOR"
  cmd_topic: "cmnd/Wemos32/power"
- id: "WemosR2"
  name: "Wemos AR"
  type: "analog"
  sensor_id: "Range2"
  status_topic: "tele/Wemos32/SENSOR"
  cmd_topic: "cmnd/Wemos32/power"
- id: "WemosT1"
  name: "Wemos T1"
  type: "Temp"
  sensor_id: "DS18B20-1"
  status_topic: "tele/Wemos32/SENSOR"
  cmd_topic: "cmnd/Wemos32/power"
- id: "WemosT2"
  name: "Wemos T2"
  type: "Temp"
  sensor_id: "DS18B20-2"
  status_topic: "tele/Wemos32/SENSOR"
  cmd_topic: "cmnd/Wemos32/power"
- id: "WemosTH"
  name: "Wemos TH"
  type: "TempHumid"
  sensor_id: "AM2301"
  status_topic: "tele/Wemos32/SENSOR"
  cmd_topic: "cmnd/Wemos32/power"
- id: "WemosSW"
  name: "Wemos SW"
  type: "switch"
  status_topic: "stat/Wemos32/POWER"
  cmd_topic: "cmnd/Wemos32/power"
```
  - Note the topic (Wemos32) is the same for all sensors on the same device  
    The 'id' and 'name' can be different

##### `"id":`

ISY node ID - Can be anything you like, but ISY restricts to alphanumeric  
characters only and underline, no special characters, **maximum 14 characters**

##### `"type":`

One of the following:

Tasmota flashed Devices: 
- *switch* - For basic sonoff or generic switch.
- *analog* - General purpose Analog input using onboard ADC. * see details below
- *s31* - This is for the [Sonoff S31][s31] energy monitoring (use switch type for control)
- *TempHumid* - For AM2301, AM2302, AM2321, DHT21, DHT22 sensors. * see details below
- *Temp* - For DS18B20 sensors. * see details below
- *TempHumidPress* - Supports the BME280 sensors.
- *ifan* - Sonoff [iFan] module - motor control, use *switch* as a separate device for light control
- *distance* - Supports HC-SR04 Ultrasonic Sensor.
- *dimmer* - Smart Wi-Fi Light Dimmer Switch, [**See Amazon**][dimmer]  
Important, use  
cmd_topic: cmnd/topic/dimmer  
status_topic: stat/topic/DIMMER (not .../power and ../POWER)
- *RGBW* - Control for a micro-controlled [RGBW strip]
- *sensor* - For nodemcu multi-sensor (see link in thread).
- *flag* - For your device to send a condition to ISY {OK,NOK,LO,HI,ERR,IN,OUT,UP,DOWN,TRIGGER,ON,OFF,---}

- *shellyflood* - [Shelly Flood sensor][Flood]; supports monitoring of  
temperature, water leak detection (`flood`), battery level, and errors. Uses Shelly's MQTT mode, not Tasmota.
- *raw* - simple str, int

- *ratgdo* - adds garage device based on the ratgdo board.  
use topic_prefix/device name for both status & command topics  
see [**ratgdo site**](https://paulwieland.github.io/ratgdo/)

##### `"status_topic":`

- For switch this will be the cmnd topic (like `cmnd/sonoff1/POWER`),  
but on sensors this will be the telemetry topic (like `tele/sonoff/SENSOR`).  
For Shelly Floods, this will be an array, like:

```json
[ "shellies/shellyflood-<unique-id>/sensor/temperature", 
   "shellies/shellyflood-<unique-id>/sensor/flood" ]  
```

(they usually also have a `battery` and `error` topic that follow the same pattern).

##### `"cmd_topic":`

- Is always required, even if the type doesn't support it (like a sensor)  
Just enter a generic topic (`cmnd/sensor/power`).  
##### `* Notes on Analog`
  - if you are using ANALOG, TEMP or TEMPHUMID 'types', you need to add this object to the configuration of the device: 
  ```json
      sensor_id: "sensor name"
  ```
 
  - the 'sensor name' can be found by examining an mqtt message in the Web  
  console of the Tasmota device



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
