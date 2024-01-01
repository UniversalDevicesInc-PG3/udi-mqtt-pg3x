
# MQTT Nodeserver for Sonoff Devices

[![license](https://img.shields.io/github/license/mashape/apistatus.svg)](https://github.com/exking/udi-mqtt-poly/blob/master/LICENSE)

This Poly provides an interface between MQTT broker and [Polyglot PG3](https://github.com/UniversalDevicesInc/pg3-dist) server.

[This thread](https://forum.universal-devices.com/topic/24538-sonoff/?tab=comments#comment-244571) on UDI forums has more details, ask questions there.

Note - your Sonoff MUST run the [Sonoff-Tasmota](https://github.com/arendst/Sonoff-Tasmota) firmware in order to work with MQTT!


 1. You will need a MQTT broker running (can be on RPi running Polyglot). (Likely already running, if you are on PG3 or PG3x on eISY)
	 -  See post #1 in [this thread](https://forum.universal-devices.com/topic/24538-sonoff) on how to setup.

 2. You will need to define the following custom parameters:
	 - `mqtt_server` - defaults to 'localhost' 
	 - `mqtt_port` - defaults to 1884, (Do not change, if you're using the default MQTT Broker in PG3x)
	 - `mqtt_user` - username for the MQTT broker  (Not used in default MQTT Broker in PG3x)
	 - `mqtt_password` - MQTT user's password  (Not used in default MQTT Broker in PG3x)
	 - `devfile` - PREFERRED METHOD - Alternative to `devlist` option below - use the yaml file instead, start with `devices:` and then same syntax
	 - `devlist` - You will need to put a JSON list of all your Sonoff devices and topics they listen to, for example:
		- `[  {"id":  "sonoff1",  "type":  "switch",  "status_topic":  "stat/sonoff1/POWER",  "cmd_topic":  "cmnd/sonoff1/power"},  {"id":  "sonoff2",  "type":  "switch",  "status_topic":  "stat/sonoff2/POWER",  "cmd_topic":  "cmnd/sonoff2/power"}  ]`
			- `"id":` ISY node ID - Can be anything you like, but ISY restricts to alphanumeric characters only and underline, no special characters, maximum 14 symbols.
			- `"type":` One of the following:
				- *switch* - For basic sonoff power switch.
				- *sensor* - For nodemcu multi-sensor (see link in thread).
                - *flag* - For your device to send a condition to ISY {OK,NOK,LO,HI,ERR,IN,OUT,UP,DOWN,TRIGGER,ON,OFF,---}
				- *TempHumid* - For AM2301, AM2302, AM2321, DHT21, DHT22,  sensors. * see details below
				- *Temp* - For DS18B20 sensors. * see details below
				- *TempHumidPress* - Supports the BME280 sensors.
				- *distance* - Supports HC-SR04 Ultrasonic Sensor.
				- *analog* - General purpose Analog input using onboard ADC. * see details below
				- *s31* - This is for the [Sonoff S31](https://www.itead.cc/sonoff-s31.html) energy monitoring (use switch type for control).
				- *RGBW* - Control for a micro-controlled RGBW strip http://github.com/sejgit/shelfstrip
				- *ifan* - Sonoff [iFan](https://itead.cc/product/sonoff-ifan03-wi-fi-ceiling-fan-and-light-controller/) module - motor control, use *switch* as a separate device for light control
                - *shellyflood* - Shelly [Flood](https://shelly-api-docs.shelly.cloud/gen1/#shelly-flood-overview) sensor; supports monitoring of temperature, water leak detection (`flood`), battery level, and errors.
                - *dimmer* - Smart Wi-Fi Light Dimmer Switch (https://www.amazon.com/Dimmer-Switch-Bresuve-Wireless-Compatible/dp/B07WRJWD28?th=1)
							Important, use cmd_topic: cmnd/topic/dimmer and status_topic: stat/topic/DIMMER (not .../power and ../POWER) 
                - *ratgdo* - adds garage device based on the ratgdo board. use topic_prefix/device name for both status & command topics. see ratgdo site for more
                  https://paulwieland.github.io/ratgdo/
			- `"status_topic":` - For switch this will be the cmnd topic (like `cmnd/sonoff1/power`), but on sensors this will be the telemetry topic (like `tele/sonoff/SENSOR`). For Shelly Floods, this will be an array, like `[ "shellies/shellyflood-<unique-id>/sensor/temperature", "shellies/shellyflood-<unique-id>/sensor/flood" ]` (they usually also have a `battery` and `error` topic that follow the same pattern).
			- `"cmd_topic":` - Is always required, even if the type doesn't support it (like a sensor).  Just enter a generic topic (`cmnd/sensor/POWER`).
    ** if you are using ANALOG, TEMP, TEMPHUMID or TEMPHUMIDPRES 'types', you need to add a <'sensor_id': 'sensor name'> object to the configuration of the device
     ** the 'sensor name' can be found by examining an MQTT message in the Web console of the Tasmota device
     ** a devfile for those sensors would look like this:

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

- ** Note that the topic (Wemos32) is the same for all sensors on the same device. The 'id' and 'name' can be different