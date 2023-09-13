# UDI Polyglot PG3x MQTT Poly

[![license](https://img.shields.io/github/license/mashape/apistatus.svg)](https://github.com/exking/udi-mqtt-poly/blob/master/LICENSE)

This Poly provides an interface between MQTT broker and Polyglot v3 server.

### Installation instructions
You can install the Node Server from the Polyglot store or manually running
```
cd ~/.polyglot/nodeservers
git clone https://github.com/Trilife/udi-mqtt-pg3x.git MQTT
cd MQTT
./install.sh
```

### Notes

This BETA version has added a DIMMER module and expanded ANALOG to include A0, Temperature, Illuminance, Range, pH and MQX. "Query" may not work!
Note: The dimmer uses hint = [4,17,0,0] to emulate a ZWave dimmer in Google Home commands
Please report any problems on the UDI user forum.

Thanks and good luck.
