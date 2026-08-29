# Changelog

## 0.50.9

- **Clear MQTT waiting notice promptly after broker connects**: drain Paho callbacks at startup and at DISCOVER so "Waiting on user MQTT connection" does not linger for a full poll cycle when the broker is already up
- **Fix devfile path resolution**: bare filename (e.g. `virtualconfig.yaml`) resolves to `data/<name>`; empty `devfile` no longer silently loads `mqtt-devices.yaml` — use an explicit devfile or `devlist`
- **Fix startup log** (was incorrectly labeled "Virtual Devices")
- **PG3 store manifest** (`server.json`) with executable `udi-mqtt-pg3x.py` — use **Update** from the store
- **Rename entry script** from `mqtt-poly.py` to `udi-mqtt-pg3x.py`
- **Standard bootstrap** (error handling; version in `VERSION` / `profile/version.txt` / `server.json`)
- **Developer toolchain**: uv, pytest profile sync test, Makefile, CONTRIBUTING (runtime install unchanged: `install.sh` + `requirements.txt`)

## 0.50.8

- Enable Paho MQTT automatic reconnect with exponential backoff (2–30s)
- Start with `connect_async()` and keep retrying when the broker is offline at startup
- Show a persistent notice while waiting for or recovering the user MQTT connection
- Reject publishes while disconnected instead of silently dropping commands
- Resubscribe to status topics only after a successful connect callback
- Defer MQTT connect/disconnect handling to the Polyglot thread to avoid races
- Subscribe only newly discovered topics during DISCOVER; skip node queries on reconnect
- Add `on_connect_fail` logging for TCP connection failures before CONNACK

## 0.50.7

- Bump pip dependencies in Pipfile.lock to resolve 12 Dependabot security alerts
- urllib3 2.5.0 → 2.7.0, requests 2.32.5 → 2.33.0, pytest 7.4.4 → 9.0.3, and related transitive updates

## 0.50.6

- Treat pip environment-resolver errors as non-fatal when plugin packages import

## 0.50.5

- Remove pip and setuptools pins from requirements.txt that blocked eisy install

## 0.50.4

- Add MQTT payload format examples to README for all sensor types
- Link POLYGLOT_CONFIG sensor section to README payload reference

## 0.50.3

- Restructure POLYGLOT_CONFIG for devfile-first setup with upload and SSH paths
- Add starter `data/mqtt-devices.yaml` template
- Trim README to capability and installation overview only

## 0.50.2

- Extract device discovery and topic registration into discovery module
- Unwrap Tasmota StatusSNS payloads once in Controller before routing to nodes
- Skip duplicate status topic registration on re-discovery
- Remove dead pass stubs from node modules
- Fix disconnect handler exception path

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
