
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
	 - `devfile` - Alternative to `devlist` option below - use the yaml file instead, start with `devices:` and then same syntax
	 - `devlist` - You will need to put a JSON list of all your Sonoff devices and topics they listen to, for example:
		- `[  {"id":  "sonoff1",  "type":  "switch",  "status_topic":  "stat/sonoff1/POWER",  "cmd_topic":  "cmnd/sonoff1/power"},  {"id":  "sonoff2",  "type":  "switch",  "status_topic":  "stat/sonoff2/POWER",  "cmd_topic":  "cmnd/sonoff2/power"}  ]`
			- `"id":` ISY node ID - Can be anything you like, but ISY restricts to alphanumeric characters only and underline, no special characters, maximum 14 symbols.
			- `"type":` One of the following:
				- *switch* - For basic sonoff power switch.
				- *sensor* - For nodemcu multisensor (see link in thread).
                - *flag* - For your device to send a condition to ISY {OK,NOK,LO,HI,ERR,IN,OUT,UP,DOWN,TRIGGER,ON,OFF,---}
				- *TempHumid* - For DHT21, DHT22, AM2301, AM2302, AM2321 sensors.
				- *Temp* - For DS18B20 sensors.
				- *TempHumidPress* - Supports the BME280 sensors.
				- *distance* - Supports HC-SR04 Ultrasonic Sensor.
				- *analog* - General purpose Analog input using onboard ADC.
				- *s31* - This is for the [Sonoff S31](https://www.itead.cc/sonoff-s31.html) energy monitoring (use switch type for control).
				- *RGBW* - Control for a micro-controlled RGBW strip http://github.com/sejgit/shelfstrip
				- *ifan* - Sonoff [iFan](https://itead.cc/product/sonoff-ifan03-wi-fi-ceiling-fan-and-light-controller/) module - motor control, use *switch* as a separate device for light control
                - *shellyflood* - Shelly [Flood](https://shelly-api-docs.shelly.cloud/gen1/#shelly-flood-overview) sensor; supports monitoring of temperature, water leak detection (`flood`), battery level, and errors.
                - *dimmer* - Smart Wi-Fi Light Dimmer Switch (https://www.amazon.com/Dimmer-Switch-Bresuve-Wireless-Compatible/dp/B07WRJWD28?th=1)
							Important, use cmd_topic: cmnd/topic/dimmer and status_topic: stat/topic/DIMMER (not .../power and ../POWER) 
			- `"status_topic":` - For switch this will be the cmnd topic (like `cmnd/sonoff1/power`), but on sensors this will be the telemetry topic (like `tele/sonoff/SENSOR`). For Shelly Floods, this will be an array, like `[ "shellies/shellyflood-<unique-id>/sensor/temperature", "shellies/shellyflood-<unique-id>/sensor/flood" ]` (they usually also have a `battery` and `error` topic that follow the same pattern).
			- `"cmd_topic":` - Is always required, even if the type doesn't support it (like a sensor).  Just enter a generic topic (`cmnd/sensor/POWER`).

