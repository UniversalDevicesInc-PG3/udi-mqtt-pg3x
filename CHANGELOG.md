# Changelog

## 0.50.1

- Fix startup handler gate when CUSTOMPARAMS arrives last
- Fix poll heartbeat guard to respect controller ready state
- Accept documented devlist JSON arrays alongside legacy dict upserts
- Merge devfile and devlist configuration as documented
- Resubscribe MQTT topics after DISCOVER when already connected
- Add MQTT connect timeout instead of infinite wait
- Fix sensor message routing to use two-argument updateInfo
- Refactor config loading, device registry, and MQTT bridge modules
- Add MQTasmotaSensor base class for shared Tasmota sensor behavior
- Unsubscribe MQTT topics when nodes are removed
- Add legacy config regression test suite

## 0.50.0

- Refactor Controller/Nodes for Pythonic style and commenting
- Add user defined default status_prefix and cmd_prefix
- Add numofnodes
- Add MQDroplet device

## 0.40.3

- Fixed typos in POLYGLOT_CONFIG.md
- Started organizing device types according to Tasmota, Sensor etc.

## 0.40.2

- README.md clean-up
- POLYGLOT_CONFIG.md clean-up

## 0.40.1

- s31 displays in program

## 0.40.0

- Change numbering to allow for branch management
- raw fix docs and allow int in addition to str
- find topic by topic if no device_id find
- discover button updates nodes and MQTT subscriptions
- config.md fixes
- status for switch device available in programs
- internal: improve logging for debug
- Changed versioning so git branches and hot fixes can work
- Switch make Status available in IF for programs
- Parameters are not initially populated; plugin uses defaults:
  - mqtt_server = LocalHost
  - mqtt_port = 1884
  - mqtt_user = admin
  - mqtt_password = admin

## 0.0.39

- DEBUG discover bug fix

## 0.0.38

- Change node throttling timer from 0.1s to 0.2s

## 0.0.37

- Re-factor files separating controller and nodes
- Fix adding and removal of nodes during start-up and/or discovery
