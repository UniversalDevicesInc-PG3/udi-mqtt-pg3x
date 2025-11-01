"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2025

node MQSensor
"""

# std libraries
import json

# external libraries
from udi_interface import Node, LOGGER

# personal libraries
pass


class MQSensor(Node):
    """Node representing a multi-sensor MQTT device."""
    id = 'mqsens'

    def __init__(self, polyglot, primary, address, name, device):
        """Initializes the MQSensor node.

        Args:
            polyglot: Reference to the Polyglot interface.
            primary: The address of the parent node.
            address: The address of this node.
            name: The name of this node.
            device: Dictionary containing device-specific information.
        """
        super().__init__(polyglot, primary, address, name)
        self.controller = self.poly.getNode(self.primary)
        self.lpfx = f'{address}:{name}'
        self.cmd_topic = device["cmd_topic"]
        self.motion = False


    def updateInfo(self, payload: str, topic: str):
        """Updates all sensor values based on a JSON payload from MQTT.

        Args:
            payload: The JSON string received from the MQTT topic.
            topic: The MQTT topic from which the message was received.
        """
        LOGGER.info(f"{self.lpfx} topic:{topic}, payload:{payload}")
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as e:
            LOGGER.error(f"Could not decode JSON payload '{payload}': {e}")
            return

        self._update_motion(data)
        self._update_environment(data)
        self._update_led(data)
        LOGGER.debug(f"{self.lpfx} Exit")


    def _update_motion(self, data: dict):
        """Updates the motion sensor driver based on payload data."""
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


    def _update_environment(self, data: dict):
        """Updates temperature, humidity, and light drivers based on payload data."""
        if "temperature" in data:
            self.setDriver("CLITEMP", data["temperature"])
        if "heatIndex" in data:
            self.setDriver("GPV", data["heatIndex"])
        if "humidity" in data:
            self.setDriver("CLIHUM", data["humidity"])
        if "ldr" in data:
            self.setDriver("LUMIN", data["ldr"])


    def _update_led(self, data: dict):
        """Updates the LED drivers based on payload data."""
        if "state" in data:
            self.setDriver("GV0", 100 if data["state"] == "ON" else 0)
        
        if "brightness" in data:
            self.setDriver("GV1", data["brightness"])
        
        if "color" in data and isinstance(data["color"], dict):
            if "r" in data["color"]:
                self.setDriver("GV2", data["color"]["r"])
            if "g" in data["color"]:
                self.setDriver("GV3", data["color"]["g"])
            if "b" in data["color"]:
                self.setDriver("GV4", data["color"]["b"])


    def led_on(self, command):
        """Handles the 'DON' command from ISY to turn the LED on."""
        LOGGER.info(f"{self.lpfx} {command}")
        self.controller.mqtt_pub(self.cmd_topic, json.dumps({"state": "ON"}))
        LOGGER.debug(f"{self.lpfx} Exit")


    def led_off(self, command):
        """Handles the 'DOF' command from ISY to turn the LED off."""
        LOGGER.info(f"{self.lpfx} {command}")
        self.controller.mqtt_pub(self.cmd_topic, json.dumps({"state": "OFF"}))
        LOGGER.debug(f"{self.lpfx} Exit")


    def led_set(self, command):
        """Handles the 'SETLED' command from ISY to set LED color and brightness."""
        LOGGER.info(f"{self.lpfx} {command}")
        query = command.get("query", {})
        red = self._check_limit(int(query.get("R.uom100", 0)))
        green = self._check_limit(int(query.get("G.uom100", 0)))
        blue = self._check_limit(int(query.get("B.uom100", 0)))
        brightness = self._check_limit(int(query.get("I.uom100", 0)))
        transition = int(query.get("D.uom58", 0))
        flash = int(query.get("F.uom58", 0))

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
        LOGGER.debug(f"{self.lpfx} Exit")


    def _check_limit(self, value: int) -> int:
        """Clamps a value between 0 and 255."""
        return max(0, min(255, value))


    def query(self, command=None):
        """Handles the 'QUERY' command from ISY.

        This is called by ISY to report all drivers for this node.
        """
        LOGGER.info(f"{self.lpfx} {command}")
        self.reportDrivers()
        LOGGER.debug(f"{self.lpfx} Exit")
        

    hint = '0x01030200'
    # home, sensor, multilevel sensor
    # Hints See: https://github.com/UniversalDevicesInc/hints


    # all the drivers - for reference
    # UOMs of interest:
    # 2: boolean
    # 17: Fahrenheit (F)
    # 22: relative humidity
    # 36: lux
    # 78: 0-Off 100-On, 101-Unknown
    # 100: A Level from 0-255
    #
    # Driver controls of interest:
    # ST: Status
    # CLITEMP: Current Temperature
    # GPV: General Purpose Value
    # CLIHUM: Humidity
    # LUMIN: Luminance
    # GV0: Custom Control 0
    # GV1: Custom Control 1
    # GV2: Custom Control 2
    # GV3: Custom Control 3
    # GV4: Custom Control 4
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


    """
    This is a dictionary of commands. If ISY sends a command to the NodeServer,
    this tells it which method to call. DON calls setOn, etc.
    """
    commands = {
        "QUERY": query,
        "DON": led_on,
        "DOF": led_off,
        "SETLED": led_set
    }
