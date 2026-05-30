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

## Help

Questions and support: [UDI MQTT forum][forum]

[license]: https://img.shields.io/github/license/mashape/apistatus.svg
[localLicense]: https://github.com/Trilife/udi-mqtt-pg3x/blob/main/LICENSE
[forum]: https://forum.universal-devices.com/forum/315-mqtt/
