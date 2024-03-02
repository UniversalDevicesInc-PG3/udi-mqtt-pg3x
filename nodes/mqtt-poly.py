#!/usr/bin/env python3


class MQSwitch(udi_interface.Node):
    def __init__(self, polyglot, primary, address, name, device):
        super().__init__(polyglot, primary, address, name)
        self.controller = self.poly.getNode(self.primary)
        self.cmd_topic = device["cmd_topic"]
        self.on = False

    def updateInfo(self, payload, topic: str):
        if payload == "ON":
            if not self.on:
                self.reportCmd("DON")
                self.on = True
            self.setDriver("ST", 100)
        elif payload == "OFF":
            if self.on:
                self.reportCmd("DOF")
                self.on = False
            self.setDriver("ST", 0)
        else:
            LOGGER.error("Invalid payload {}".format(payload))

    def set_on(self, command):
        self.on = True
        self.controller.mqtt_pub(self.cmd_topic, "ON")

    def set_off(self, command):
        self.on = False
        self.controller.mqtt_pub(self.cmd_topic, "OFF")

    def query(self, command=None):
        self.controller.mqtt_pub(self.cmd_topic, "")
        self.reportDrivers()

    drivers = [{"driver": "ST", "value": 0, "uom": 78, "name": "Power"}]

    id = "MQSW"
    hint = [4, 2, 0, 0]
    commands = {"QUERY": query, "DON": set_on, "DOF": set_off}


# Class for a single channel Dimmer. 
# Currently, supports RJWF-02A
class MQDimmer(udi_interface.Node):
    def __init__(self, polyglot, primary, address, name, device):
        super().__init__(polyglot, primary, address, name)
        self.controller = self.poly.getNode(self.primary)
        self.cmd_topic = device["cmd_topic"]
        self.status_topic = device['status_topic']
        self.dimmer = 0

    def updateInfo(self, payload, topic: str):
        power = ''
        dimmer = ''
        try:
            data = json.loads(payload)
            if 'Dimmer' in data:
                dimmer = int(data['Dimmer'])
            else:
                dimmer = self.dimmer
            if 'POWER' in data:
                power = data['POWER']
            LOGGER.info("Dimmer = {} , Power = {}".format(dimmer, power))
        except Exception as ex:
            LOGGER.error(f"Could not decode payload {payload}: {ex}")
            return False
        if power == 'ON' or (self.dimmer == 0 and dimmer > 0):
            self.reportCmd("DON")
            self.dimmer = dimmer
            self.setDriver('ST', self.dimmer)
        if power == 'OFF' or (self.dimmer > 0 and dimmer == 0):
            self.reportCmd("DOF")
            self.setDriver('ST', 0)

    def set_on(self, command):
        try:
            if command.get('value') is not None:
                self.dimmer = int(command.get('value'))
        except Exception as ex:
            LOGGER.error(f"Unexpected Dim-Value {ex}, turning to 10%")
            self.dimmer = 10
        if self.dimmer == 0:
            self.dimmer = 10
        self.setDriver('ST', self.dimmer)
        self.controller.mqtt_pub(self.cmd_topic, self.dimmer)

    def set_off(self, command):
        self.controller.mqtt_pub(self.cmd_topic, 0)
        self.setDriver('ST', self.dimmer)

    def brighten(self, command):
        if self.dimmer <= 90:
            self.dimmer += 10
        else:
            self.dimmer = 100
        self.controller.mqtt_pub(self.cmd_topic, self.dimmer)
        self.setDriver('ST', self.dimmer)

    def dim(self, command):
        if self.dimmer >= 10:
            self.dimmer -= 10
        else:
            self.dimmer = 0
        self.controller.mqtt_pub(self.cmd_topic, self.dimmer)
        self.setDriver('ST', self.dimmer)

    def query(self, command=None):
        query_topic = self.cmd_topic.rsplit('/', 1)[0] + '/State'
        self.controller.mqtt_pub(query_topic, "")
        LOGGER.info("STATUS_TOPIC = {}".format(self.status_topic))
        self.reportDrivers()

    drivers = [{'driver': 'ST', 'value': 0, 'uom': 51, 'name': 'Status'}]

    id = "MQDIMMER"
    hint = [1, 2, 9, 0]
    commands = {"QUERY": query, "DON": set_on, "DOF": set_off, "BRT": brighten, "DIM": dim}


class MQFan(udi_interface.Node):
    def __init__(self, polyglot, primary, address, name, device):
        super().__init__(polyglot, primary, address, name)
        self.controller = self.poly.getNode(self.primary)
        self.cmd_topic = device["cmd_topic"]
        self.fan_speed = 0

    def updateInfo(self, payload, topic: str):
        try:
            json_payload = json.loads(payload)
            fan_speed = int(json_payload['FanSpeed'])
        except Exception as ex:
            LOGGER.error(f"Could not decode payload {payload}: {ex}")
        if 4 < fan_speed < 0:
            LOGGER.error(f"Unexpected Fan Speed {fan_speed}")
            return
        if self.fan_speed == 0 and fan_speed > 0:
            self.reportCmd("DON")
        if self.fan_speed > 0 and fan_speed == 0:
            self.reportCmd("DOF")
        self.fan_speed = fan_speed
        self.setDriver("ST", self.fan_speed)

    def set_on(self, command):
        try:
            self.fan_speed = int(command.get('value'))
        except Exception as ex:
            LOGGER.info(f"Unexpected Fan Speed {ex}, assuming High")
            self.fan_speed = 3
        if 4 < self.fan_speed < 0:
            LOGGER.error(f"Unexpected Fan Speed {self.fan_speed}, assuming High")
            self.fan_speed = 3
        self.setDriver("ST", self.fan_speed)
        self.controller.mqtt_pub(self.cmd_topic, self.fan_speed)

    def set_off(self, command):
        self.fan_speed = 0
        self.setDriver("ST", self.fan_speed)
        self.controller.mqtt_pub(self.cmd_topic, self.fan_speed)

    def speed_up(self, command):
        self.controller.mqtt_pub(self.cmd_topic, "+")

    def speed_down(self, command):
        self.controller.mqtt_pub(self.cmd_topic, "-")

    def query(self, command=None):
        self.controller.mqtt_pub(self.cmd_topic, "")
        self.reportDrivers()

    drivers = [{"driver": "ST", "value": 0, "uom": 25}]

    id = "MQFAN"
    hint = [4, 2, 0, 0]
    commands = {"QUERY": query, "DON": set_on, "DOF": set_off, "FDUP": speed_up, "FDDOWN": speed_down}


class MQSensor(udi_interface.Node):
    def __init__(self, polyglot, primary, address, name, device):
        super().__init__(polyglot, primary, address, name)
        self.controller = self.poly.getNode(self.primary)
        self.cmd_topic = device["cmd_topic"]
        self.on = False
        self.motion = False

    def updateInfo(self, payload, topic: str):
        try:
            data = json.loads(payload)
        except Exception as ex:
            LOGGER.error("Failed to parse MQTT Payload as Json: {} {}".format(ex, payload))
            return False

        # motion detector
        if "motion" in data:
            if data["motion"] == "standby":
                self.setDriver("ST", 0)
                if self.motion:
                    self.motion = False
                    self.reportCmd("DOF")
            else:
                self.setDriver("ST", 1)
                if not self.motion:
                    self.motion = True
                    self.reportCmd("DON")
        else:
            self.setDriver("ST", 0)
        # temperature
        if "temperature" in data:
            self.setDriver("CLITEMP", data["temperature"])
        # heatIndex
        if "heatIndex" in data:
            self.setDriver("GPV", data["heatIndex"])
        # humidity
        if "humidity" in data:
            self.setDriver("CLIHUM", data["humidity"])
        # light detector reading
        if "ldr" in data:
            self.setDriver("LUMIN", data["ldr"])
        # LED
        if "state" in data:
            # LED is present
            if data["state"] == "ON":
                self.setDriver("GV0", 100)
            else:
                self.setDriver("GV0", 0)
            if "brightness" in data:
                self.setDriver("GV1", data["brightness"])
            if "color" in data:
                if "r" in data["color"]:
                    self.setDriver("GV2", data["color"]["r"])
                if "g" in data["color"]:
                    self.setDriver("GV3", data["color"]["g"])
                if "b" in data["color"]:
                    self.setDriver("GV4", data["color"]["b"])

    def led_on(self, command):
        self.controller.mqtt_pub(self.cmd_topic, json.dumps({"state": "ON"}))

    def led_off(self, command):
        self.controller.mqtt_pub(self.cmd_topic, json.dumps({"state": "OFF"}))

    def led_set(self, command):
        query = command.get("query")
        red = self._check_limit(int(query.get("R.uom100")))
        green = self._check_limit(int(query.get("G.uom100")))
        blue = self._check_limit(int(query.get("B.uom100")))
        brightness = self._check_limit(int(query.get("I.uom100")))
        transition = int(query.get("D.uom58"))
        flash = int(query.get("F.uom58"))
        cmd = {
            "state": "ON",
            "brightness": brightness,
            "color": {"r": red, "g": green, "b": blue},
        }
        if transition > 0:
            cmd["transition"] = transition
        if flash > 0:
            cmd["flash"] = flash
        self.controller.mqtt_pub(self.cmd_topic, json.dumps(cmd))

    def _check_limit(self, value):
        if value > 255:
            return 255
        elif value < 0:
            return 0
        else:
            return value

    def query(self, command=None):
        self.reportDrivers()

    drivers = [
        {"driver": "ST", "value": 0, "uom": 2},
        {"driver": "CLITEMP", "value": 0, "uom": 17},
        {"driver": "GPV", "value": 0, "uom": 17},
        {"driver": "CLIHUM", "value": 0, "uom": 22},
        {"driver": "LUMIN", "value": 0, "uom": 36},
        {"driver": "GV0", "value": 0, "uom": 78},
        {"driver": "GV1", "value": 0, "uom": 100},
        {"driver": "GV2", "value": 0, "uom": 100},
        {"driver": "GV3", "value": 0, "uom": 100},
        {"driver": "GV4", "value": 0, "uom": 100},
    ]

    id = "MQSENS"

    commands = {"QUERY": query, "DON": led_on, "DOF": led_off, "SETLED": led_set}

    # this is meant as a flag for if you have a sensor or condition on your IOT device
    # which you want the device program rather than the ISY to flag
    # FLAG-0 = OK
    # FLAG-1 = NOK
    # FLAG-2 = LO
    # FLAG-3 = HI
    # FLAG-4 = ERR
    # FLAG-5 = IN
    # FLAG-6 = OUT
    # FLAG-7 = UP
    # FLAG-8 = DOWN
    # FLAG-9 = TRIGGER
    # FLAG-10 = ON
    # FLAG-11 = OFF
    # FLAG-12 = ---
    # payload is direct (like SW) not JSON encoded (like SENSOR)
    # example device: liquid float {OK, LO, HI}
    # example condition: IOT devices sensor connections {OK, NOK, ERR(OR)}


class MQFlag(udi_interface.Node):
    def __init__(self, polyglot, primary, address, name, device):
        super().__init__(polyglot, primary, address, name)
        self.controller = self.poly.getNode(self.primary)
        self.cmd_topic = device["cmd_topic"]

    def updateInfo(self, payload, topic: str):
        if payload == "OK":
            self.setDriver("ST", 0)
        elif payload == "NOK":
            self.setDriver("ST", 1)
        elif payload == "LO":
            self.setDriver("ST", 2)
        elif payload == "HI":
            self.setDriver("ST", 3)
        elif payload == "IN":
            self.setDriver("ST", 5)
        elif payload == "OUT":
            self.setDriver("ST", 6)
        elif payload == "UP":
            self.setDriver("ST", 7)
        elif payload == "DOWN":
            self.setDriver("ST", 8)
        elif payload == "TRIGGER":
            self.setDriver("ST", 9)
        elif payload == "ON":
            self.setDriver("ST", 10)
        elif payload == "OFF":
            self.setDriver("ST", 11)
        elif payload == "---":
            self.setDriver("ST", 12)
        else:
            LOGGER.error("Invalid payload {}".format(payload))
            payload = "ERR"
            self.setDriver("ST", 4)

    def reset_send(self, command):
        self.controller.mqtt_pub(self.cmd_topic, "RESET")

    def query(self, command=None):
        self.controller.mqtt_pub(self.cmd_topic, "")
        self.reportDrivers()

    drivers = [{"driver": "ST", "value": 0, "uom": 25}]

    id = "MQFLAG"
    commands = {"QUERY": query, "RESET": reset_send}


# This class adds support for temperature/humidity/Dewpoint sensors.
# It was originally developed with an AM2301
class MQdht(udi_interface.Node):
    def __init__(self, polyglot, primary, address, name, device):
        super().__init__(polyglot, primary, address, name)
        self.controller = self.poly.getNode(self.primary)
        LOGGER.debug(f'DEVCLASS: {device} ')
        self.cmd_topic = device["cmd_topic"]
        if 'sensor_id' in device:
            self.sensor_id = device['sensor_id']
        else:
            self.sensor_id = 'SINGLE_SENSOR'
            device['sensor_id'] = self.sensor_id
        LOGGER.debug(f'CMD_ID {self.sensor_id}, {self.cmd_topic}')
        self.on = False

    def updateInfo(self, payload, topic: str):
        try:
            data = json.loads(payload)
        except Exception as ex:
            LOGGER.error("Failed to parse MQTT Payload as Json: {} {}".format(ex, payload))
            return False
        LOGGER.debug(f'ZZZ {self.sensor_id}, {data} ')
        if 'StatusSNS' in data:
            data = data['StatusSNS']
        if self.sensor_id in data:
            self.setDriver("ST", 1)
            # self.setDriver("ERR", 0)
            self.setDriver("CLITEMP", data[self.sensor_id]["Temperature"])
            self.setDriver("CLIHUM", data[self.sensor_id]["Humidity"])
            self.setDriver("DEWPT", data[self.sensor_id]["DewPoint"])
        else:
            self.setDriver("ST", 0)
            # self.setDriver("ERR", 1)

    def query(self, command=None):
        LOGGER.debug(f'QUERY: {self.sensor_id}')
        query_topic = self.cmd_topic.rsplit('/', 1)[0] + '/Status'
        LOGGER.debug(f'QT: {query_topic}')
        self.controller.mqtt_pub(query_topic, " 10")
        self.reportDrivers()

    drivers = [
        {"driver": "ST", "value": 0, "uom": 2, "name": "AM2301 ST"},
        {"driver": "CLITEMP", "value": 0, "uom": 17, "name": "Temperature"},
        {"driver": "CLIHUM", "value": 0, "uom": 22, "name": "Humidity"},
        {"driver": "DEWPT", "value": 0, "uom": 17, "name": "Dew Point"},
        # {"driver": "ERR", "value": 0, "uom": 2}
    ]

    id = "MQDHT"

    commands = {"QUERY": query}


# This class is an attempt to add support for temperature only sensors.
# was made for DS18B20 waterproof
class MQds(udi_interface.Node):
    def __init__(self, polyglot, primary, address, name, device):
        super().__init__(polyglot, primary, address, name)
        self.controller = self.poly.getNode(self.primary)
        LOGGER.debug(f'DEVCLASS: {device} ')
        self.cmd_topic = device["cmd_topic"]
        if 'sensor_id' in device:
            self.sensor_id = device['sensor_id']
        else:
            self.sensor_id = 'SINGLE_SENSOR'
            device['sensor_id'] = self.sensor_id
        LOGGER.debug(f'CMD_ID {self.sensor_id}, {self.cmd_topic}')
        self.on = False

    def start(self):
        pass

    def updateInfo(self, payload, topic: str):
        try:
            data = json.loads(payload)
        except Exception as ex:
            LOGGER.error("Failed to parse MQTT Payload as Json: {} {}".format(ex, payload))
            return False
        LOGGER.debug(f'YYY {self.sensor_id}, {data} ')
        if 'StatusSNS' in data:
            data = data['StatusSNS']
        if self.sensor_id in data:
            self.setDriver("ST", 1)
            self.setDriver("CLITEMP", data[self.sensor_id]["Temperature"])
        else:
            self.setDriver("ST", 0)
            self.setDriver("GPV", 0)

    def query(self, command=None):
        LOGGER.debug(f'QUERY: {self.sensor_id}')
        query_topic = self.cmd_topic.rsplit('/', 1)[0] + '/Status'
        LOGGER.debug(f'QT: {query_topic}')
        self.controller.mqtt_pub(query_topic, " 10")
        self.reportDrivers()

    drivers = [
        {"driver": "ST", "value": 0, "uom": 2, "name": "DS18B20 ST"},
        {"driver": "CLITEMP", "value": 0, "uom": 17, "name": "Temperature"},
    ]

    id = "MQDS"

    commands = {"QUERY": query}


# This class is an attempt to add support for temperature/humidity/pressure sensors.
# Currently, supports the BME280.  Could be extended to accept others.
class MQbme(udi_interface.Node):
    def __init__(self, polyglot, primary, address, name, device):
        super().__init__(polyglot, primary, address, name)
        self.controller = self.poly.getNode(self.primary)
        LOGGER.debug(f'DEVCLASS: {device} ')
        self.cmd_topic = device["cmd_topic"]
        if 'sensor_id' in device:
            self.sensor_id = device['sensor_id']
        else:
            self.sensor_id = 'SINGLE_SENSOR'
            device['sensor_id'] = self.sensor_id
        LOGGER.debug(f'CMD_ID {self.sensor_id}, {self.cmd_topic}')
        self.on = False

    def updateInfo(self, payload, topic: str):
        try:
            data = json.loads(payload)
        except Exception as ex:
            LOGGER.error("Failed to parse MQTT Payload as Json: {} {}".format(ex, payload))
            return False
        LOGGER.debug(f'BBB {self.sensor_id}, {data} ')
        if 'StatusSNS' in data:
            data = data['StatusSNS']
        if self.sensor_id in data:
            self.setDriver("ST", 1)
            self.setDriver("CLITEMP", data[self.sensor_id]["Temperature"])
            self.setDriver("CLIHUM", data[self.sensor_id]["Humidity"])
            self.setDriver("DEWPT", data[self.sensor_id]["DewPoint"])
            # Converting to Hg, could do this in sonoff-Tasmota
            # or just report the raw hPA (or convert to kPA).
            press = format(
                round(float(".02952998751") * float(data[self.sensor_id]["Pressure"]), 2)
            )
            self.setDriver("BARPRES", press)
        else:
            self.setDriver("ST", 0)

    def query(self, command=None):
        LOGGER.debug(f'QUERY: {self.sensor_id}')
        query_topic = self.cmd_topic.rsplit('/', 1)[0] + '/Status'
        LOGGER.debug(f'QT: {query_topic}')
        self.controller.mqtt_pub(query_topic, " 10")
        self.reportDrivers()

    drivers = [
        {"driver": "ST", "value": 0, "uom": 2, "name": "Status"},
        {"driver": "CLITEMP", "value": 0, "uom": 17, "name": "Temperature"},
        {"driver": "CLIHUM", "value": 0, "uom": 22, "name": "Humidity"},
        {"driver": "DEWPT", "value": 0, "uom": 17, "name": "Dew Point"},
        {"driver": "BARPRES", "value": 0, "uom": 23},
    ]

    id = "MQBME"

    commands = {"QUERY": query}


# This class is an attempt to add support for HC-SR04 Ultrasonic Sensor.
# Returns distance in centimeters.
class MQhcsr(udi_interface.Node):
    def __init__(self, polyglot, primary, address, name, device):
        super().__init__(polyglot, primary, address, name)
        self.on = False

    def updateInfo(self, payload, topic: str):
        try:
            data = json.loads(payload)
        except Exception as ex:
            LOGGER.error(
                "Failed to parse MQTT Payload as Json: {} {}".format(ex, payload)
            )
            return False
        if "SR04" in data:
            self.setDriver("ST", 1)
            self.setDriver("DISTANC", data["SR04"]["Distance"])
        else:
            self.setDriver("ST", 0)
            self.setDriver("DISTANC", 0)

    def query(self, command=None):
        self.reportDrivers()

    drivers = [
        {"driver": "ST", "value": 0, "uom": 2},
        {"driver": "DISTANC", "value": 0, "uom": 5},
    ]

    id = "MQHCSR"

    commands = {"QUERY": query}


# Adding support for the Shelly Flood class of devices. Notably, Shellies publish their statuses on multiple
# single-value topics, rather than a single topic with a JSON object for the status. You will need to pass
# an array for the status_topic value in the JSON definition; see the POLYGLOT_CONFIG.md for details.
class ShellyFlood(udi_interface.Node):
    def __init__(self, polyglot, primary, address, name, device):
        super().__init__(polyglot, primary, address, name)
        self.on = False
        self.device = device

    def start(self):
        return True

    def updateInfo(self, payload, topic: str):
        LOGGER.debug(f"Attempting to handle message for Shelly on topic {topic} with payload {payload}")
        topic_suffix = topic.split('/')[-1]
        self.setDriver("ST", 1)
        if topic_suffix == "temperature":
            self.setDriver("CLITEMP", payload)
        elif topic_suffix == "flood":
            value = payload == "true"
            self.setDriver("GV0", value)
        elif topic_suffix == "battery":
            self.setDriver("BATLVL", payload)
        elif topic_suffix == "error":
            self.setDriver("GPV", payload)
        else:
            LOGGER.warn(f"Unable to handle data for topic {topic}")

    def query(self, command=None):
        self.reportDrivers()

    # UOMs of interest:
    # 17 = degrees F (temp)
    # 2 = boolean (flood)
    # 51 = percent (battery)
    # 56 = raw value from device (error)

    # Driver controls of interest:
    # BATLVL = battery level
    # CLITEMP = current temperature
    # GPV = general purpose value
    # GV0 = custom control 0

    drivers = [
        {"driver": "ST", "value": 0, "uom": 2},
        {"driver": "CLITEMP", "value": 0, "uom": 17},  # Temperature sensor
        {"driver": "GV0", "value": 0, "uom": 2},  # flood or not
        {"driver": "BATLVL", "value": 0, "uom": 51},  # battery level indicator
        {"driver": "GPV", "value": 0, "uom": 56},  # error code
    ]

    id = "SHFLOOD"

    commands = {"QUERY", query}


# General purpose Analog input using ADC.
class MQAnalog(udi_interface.Node):
    def __init__(self, polyglot, primary, address, name, device):
        super().__init__(polyglot, primary, address, name)
        self.controller = self.poly.getNode(self.primary)
        self.cmd_topic = device["cmd_topic"]
        if 'sensor_id' in device:
            self.sensor_id = device['sensor_id']
        else:
            self.sensor_id = 'SINGLE_SENSOR'
            device['sensor_id'] = self.sensor_id
        LOGGER.debug(f'CMD_ID {self.sensor_id}, {self.cmd_topic}')
        self.on = False

    def updateInfo(self, payload, topic: str):
        try:
            data = json.loads(payload)
        except Exception as ex:
            LOGGER.error("Failed to parse MQTT Payload as Json: {} {}".format(ex, payload))
            return False
        LOGGER.debug(f'XXX {self.sensor_id}, {data} ')
        if 'StatusSNS' in data:
            data = data['StatusSNS']
        if "ANALOG" in data:
            self.setDriver("ST", 1)
            LOGGER.debug(f'sensor_id UpdateInfo: {self.sensor_id}')
            if self.sensor_id is not 'SINGLE_SENSOR':
                self.setDriver("GPV", data["ANALOG"][self.sensor_id])
                LOGGER.info(f'M-analog {self.sensor_id}:  {data["ANALOG"][self.sensor_id]}')
            else:
                for key, value in data['ANALOG'].items():  # look for the ONLY reading inside 'ANALOG'
                    LOGGER.info(f'single analog {key}: {value}')
                    self.setDriver("GPV", value)
        else:
            LOGGER.debug(f'NOANALOG: {self.sensor_id}')
            self.setDriver("ST", 0)
            self.setDriver("GPV", 0)


    def query(self, command=None):
        LOGGER.debug(f'QUERY: {self.sensor_id}')
        query_topic = self.cmd_topic.rsplit('/', 1)[0] + '/Status'
        LOGGER.debug(f'QT: {query_topic}')
        self.controller.mqtt_pub(query_topic, " 10")
        self.reportDrivers()

    # GPV = "General Purpose Value"
    # UOM:56 = "The raw value reported by device"
    drivers = [
        {"driver": "ST", "value": 0, "uom": 2, "name": "Analog ST"},
        {"driver": "GPV", "value": 0, "uom": 56, "name": "Analog"}
    ]

    id = "MQANAL"

    commands = {"QUERY": query}


# Reading the telemetry data for a Sonoff S31 (use the switch for control)
class MQs31(udi_interface.Node):
    def __init__(self, polyglot, primary, address, name, device):
        super().__init__(polyglot, primary, address, name)
        self.on = False

    def updateInfo(self, payload, topic: str):
        try:
            data = json.loads(payload)
        except Exception as ex:
            LOGGER.error(
                "Failed to parse MQTT Payload as Json: {} {}".format(ex, payload)
            )
            return False
        if "ENERGY" in data:
            self.setDriver("ST", 1)
            self.setDriver("CC", data["ENERGY"]["Current"])
            self.setDriver("CPW", data["ENERGY"]["Power"])
            self.setDriver("CV", data["ENERGY"]["Voltage"])
            self.setDriver("PF", data["ENERGY"]["Factor"])
            self.setDriver("TPW", data["ENERGY"]["Total"])
        else:
            self.setDriver("ST", 0)

    def query(self, command=None):
        self.reportDrivers()

    drivers = [
        {"driver": "ST", "value": 0, "uom": 2},
        {"driver": "CC", "value": 0, "uom": 1},
        {"driver": "CPW", "value": 0, "uom": 73},
        {"driver": "CV", "value": 0, "uom": 72},
        {"driver": "PF", "value": 0, "uom": 53},
        {"driver": "TPW", "value": 0, "uom": 33},
    ]

    id = "MQS31"

    commands = {"QUERY": query}


class MQraw(udi_interface.Node):
    def __init__(self, polyglot, primary, address, name, device):
        super().__init__(polyglot, primary, address, name)
        self.cmd_topic = device["cmd_topic"]
        self.on = False

    def updateInfo(self, payload, topic: str):
        try:
            self.setDriver("ST", 1)
            self.setDriver("GV1", int(payload))
        except Exception as ex:
            LOGGER.error("Failed to parse MQTT Payload: {} {}".format(ex, payload))

    def query(self, command=None):
        self.reportDrivers()

    drivers = [
        {"driver": "ST", "value": 0, "uom": 2},
        {"driver": "GV1", "value": 0, "uom": 56},
    ]

    id = "MQR"
    commands = {"QUERY": query}


# Class for an RGBW strip powered through a microController running MQTT client
# able to set colours and run different transition programs
class MQRGBWstrip(udi_interface.Node):
    def __init__(self, polyglot, primary, address, name, device):
        super().__init__(polyglot, primary, address, name)
        self.controller = self.poly.getNode(self.primary)
        self.cmd_topic = device["cmd_topic"]
        self.on = False
        self.motion = False

    def updateInfo(self, payload, topic: str):
        try:
            data = json.loads(payload)
        except Exception as ex:
            LOGGER.error(
                "Failed to parse MQTT Payload as Json: {} {}".format(ex, payload)
            )
            return False

        # LED
        if "state" in data:
            # LED is present
            if data["state"] == "ON":
                self.setDriver("GV0", 100)
            else:
                self.setDriver("GV0", 0)
            if "br" in data:
                self.setDriver("GV1", data["br"])
            if "c" in data:
                if "r" in data["c"]:
                    self.setDriver("GV2", data["c"]["r"])
                if "g" in data["c"]:
                    self.setDriver("GV3", data["c"]["g"])
                if "b" in data["c"]:
                    self.setDriver("GV4", data["c"]["b"])
                if "w" in data["c"]:
                    self.setDriver("GV5", data["c"]["w"])
            if "pgm" in data:
                self.setDriver("GV6", data["pgm"])

    def led_on(self, command):
        self.controller.mqtt_pub(self.cmd_topic, json.dumps({"state": "ON"}))

    def led_off(self, command):
        self.controller.mqtt_pub(self.cmd_topic, json.dumps({"state": "OFF"}))

    def rgbw_set(self, command):
        query = command.get("query")
        red = self._check_limit(int(query.get("STRIPR.uom100")))
        green = self._check_limit(int(query.get("STRIPG.uom100")))
        blue = self._check_limit(int(query.get("STRIPB.uom100")))
        white = self._check_limit(int(query.get("STRIPW.uom100")))
        brightness = self._check_limit(int(query.get("STRIPI.uom100")))
        program = self._check_limit(int(query.get("STRIPP.uom100")))
        cmd = {
            "state": "ON",
            "br": brightness,
            "c": {"r": red, "g": green, "b": blue, "w": white},
            "pgm": program,
        }

        self.controller.mqtt_pub(self.cmd_topic, json.dumps(cmd))

    def _check_limit(self, value):
        if value > 255:
            return 255
        elif value < 0:
            return 0
        else:
            return value

    def query(self, command=None):
        self.reportDrivers()

    drivers = [
        {"driver": "ST", "value": 0, "uom": 2},
        {"driver": "GV0", "value": 0, "uom": 78},
        {"driver": "GV1", "value": 0, "uom": 100},
        {"driver": "GV2", "value": 0, "uom": 100},
        {"driver": "GV3", "value": 0, "uom": 100},
        {"driver": "GV4", "value": 0, "uom": 100},
        {"driver": "GV5", "value": 0, "uom": 100},
        {"driver": "GV6", "value": 0, "uom": 100},
    ]

    id = "MQRGBW"

    commands = {"QUERY": query, "DON": led_on, "DOF": led_off, "SETRGBW": rgbw_set}


# Class for Ratgdo Garage door opener for MYQ replacement
# Able to control door, light, lock and get status of same as well as motion, obstruction
class MQratgdo(udi_interface.Node):
    def __init__(self, polyglot, primary, address, name, device):
        super().__init__(polyglot, primary, address, name)
        self.controller = self.poly.getNode(self.primary)
        self.cmd_topic = device["cmd_topic"] + "/command/"

    def updateInfo(self, payload, topic: str):
        topic_suffix = topic.split('/')[-1]
        if topic_suffix == "availability":
            value = int(payload == "online")
            self.setDriver("ST", value)
        elif topic_suffix == "light":
            value = int(payload == "on")
            self.setDriver("GV0", value)
        elif topic_suffix == "door":
            if payload == "open":
                value = 1
            elif payload == "opening":
                value = 2
            elif payload == "stopped":
                value = 3
            elif payload == "closing":
                value = 4
            else:
                value = 0
            self.setDriver("GV1", value)
        elif topic_suffix == "motion":
            value = int(payload == "detected")
            self.setDriver("GV2", value)
        elif topic_suffix == "lock":
            value = int(payload == "locked")
            self.setDriver("GV3", value)
        elif topic_suffix == "obstruction":
            value = int(payload == "obstructed")
            self.setDriver("GV4", value)
        else:
            LOGGER.warn(f"Unable to handle data for topic {topic}")

    def lt_on(self, command):
        self.controller.mqtt_pub(self.cmd_topic + "light", "on")

    def lt_off(self, command):
        self.controller.mqtt_pub(self.cmd_topic + "light", "off")

    def dr_open(self, command):
        self.controller.mqtt_pub(self.cmd_topic + "door", "open")

    def dr_close(self, command):
        self.controller.mqtt_pub(self.cmd_topic + "door", "close")

    def dr_stop(self, command):
        self.controller.mqtt_pub(self.cmd_topic + "door", "stop")

    def lk_lock(self, command):
        self.controller.mqtt_pub(self.cmd_topic + "lock", "lock")

    def lk_unlock(self, command):
        self.controller.mqtt_pub(self.cmd_topic + "lock", "unlock")

    def query(self, command=None):
        self.reportDrivers()

    drivers = [
        {"driver": "ST", "value": 0, "uom": 2},
        {"driver": "GV0", "value": 0, "uom": 2},
        {"driver": "GV1", "value": 0, "uom": 25},
        {"driver": "GV2", "value": 0, "uom": 2},
        {"driver": "GV3", "value": 0, "uom": 2},
        {"driver": "GV4", "value": 0, "uom": 2},
    ]

    id = "MQRATGDO"

    commands = {"QUERY": query, "DON": lt_on, "DOF": lt_off, "OPEN": dr_open, "CLOSE": dr_close, "STOP": dr_stop,
                "LOCK": lk_lock, "UNLOCK": lk_unlock}


if __name__ == "__main__":
    try:
        polyglot = udi_interface.Interface([])
        polyglot.start(VERSION)
        Controller(polyglot, 'mqctrl', 'mqctrl', 'MQTT')
        polyglot.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
