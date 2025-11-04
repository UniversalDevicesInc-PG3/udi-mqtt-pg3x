"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2025

node MQRGBWstrip

Class for an RGBW strip powered through a microController running MQTT client
able to set colours and run different transition programs
"""

# std libraries
import json

# external libraries
from udi_interface import Node, LOGGER

# personal libraries
pass

# Constants
LED_ON_VALUE = 100
LED_OFF_VALUE = 0
COLOR_MAX_VALUE = 255


class MQRGBWstrip(Node):
    """Node representing an RGBW LED strip controller."""
    id = 'mqrgbw'

    def __init__(self, polyglot, primary, address, name, device):
        """Initializes the MQRGBWstrip node.

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


    def updateInfo(self, payload: str, topic: str):
        """Updates LED strip state based on a JSON payload from MQTT."""
        LOGGER.info(f"{self.lpfx} topic:{topic}, payload:{payload}")
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as e:
            LOGGER.error(f"Could not decode JSON payload '{payload}': {e}")
            return

        self._update_led_state(data)
        LOGGER.debug(f"{self.lpfx} Exit")


    def _update_led_state(self, data: dict):
        """Updates LED drivers based on parsed payload data."""
        if "state" in data:
            if data["state"] == "ON":
                self.setDriver("GV0", LED_ON_VALUE)
                self.reportCmd("DON")
            else:
                self.setDriver("GV0", LED_OFF_VALUE)
                self.reportCmd("DOF")
        
        if "br" in data:
            self.setDriver("GV1", data["br"])
        
        color_data = data.get("c")
        if isinstance(color_data, dict):
            self.setDriver("GV2", color_data.get("r"))
            self.setDriver("GV3", color_data.get("g"))
            self.setDriver("GV4", color_data.get("b"))
            self.setDriver("GV5", color_data.get("w"))
        
        if "pgm" in data:
            self.setDriver("GV6", data["pgm"])


    def led_on(self, command):
        """Handles the 'DON' command from ISY to turn the LED strip on."""
        LOGGER.info(f"{self.lpfx} {command}")
        self.controller.mqtt_pub(self.cmd_topic, json.dumps({"state": "ON"}))
        LOGGER.debug(f"{self.lpfx} Exit")


    def led_off(self, command):
        """Handles the 'DOF' command from ISY to turn the LED strip off."""
        LOGGER.info(f"{self.lpfx} {command}")
        self.controller.mqtt_pub(self.cmd_topic, json.dumps({"state": "OFF"}))
        LOGGER.debug(f"{self.lpfx} Exit")


    def rgbw_set(self, command):
        """Handles the 'SETRGBW' command from ISY to set RGBW values and program."""
        LOGGER.info(f"{self.lpfx} {command}")
        query = command.get("query", {})
        red = self._check_limit(int(query.get("STRIPR.uom100", 0)))
        green = self._check_limit(int(query.get("STRIPG.uom100", 0)))
        blue = self._check_limit(int(query.get("STRIPB.uom100", 0)))
        white = self._check_limit(int(query.get("STRIPW.uom100", 0)))
        brightness = self._check_limit(int(query.get("STRIPI.uom100", 0)))
        program = self._check_limit(int(query.get("STRIPP.uom100", 0)))
        
        cmd = {
            "state": "ON",
            "br": brightness,
            "c": {"r": red, "g": green, "b": blue, "w": white},
            "pgm": program,
        }

        self.controller.mqtt_pub(self.cmd_topic, json.dumps(cmd))
        LOGGER.debug(f"{self.lpfx} Exit")


    def _check_limit(self, value: int) -> int:
        """Clamps a value between 0 and COLOR_MAX_VALUE."""
        return max(0, min(COLOR_MAX_VALUE, value))


    def query(self, command=None):
        """Handles the 'QUERY' command from ISY.

        This is called by ISY to report all drivers for this node.
        """
        LOGGER.info(f"{self.lpfx} {command}")
        self.reportDrivers()
        LOGGER.debug(f"{self.lpfx} Exit")
        

    """
    UOMs:
    2: boolean
    78: 0-Off 100-On, 101-Unknown
    100: A Level from 0-255

    Driver controls:
    ST: Status
    GV0: Custom Control 0 (State)
    GV1: Custom Control 1 (Brightness)
    GV2: Custom Control 2 (Red)
    GV3: Custom Control 3 (Green)
    GV4: Custom Control 4 (Blue)
    GV5: Custom Control 5 (White)
    GV6: Custom Control 6 (Program)
    """
    drivers = [
        {"driver": "ST", "value": 0, "uom": 2, "name": "Status"},
        {"driver": "GV0", "value": 0, "uom": 78, "name": "State"},
        {"driver": "GV1", "value": 0, "uom": 100, "name": "Brightness"},
        {"driver": "GV2", "value": 0, "uom": 100, "name": "Red"},
        {"driver": "GV3", "value": 0, "uom": 100, "name": "Green"},
        {"driver": "GV4", "value": 0, "uom": 100, "name": "Blue"},
        {"driver": "GV5", "value": 0, "uom": 100, "name": "White"},
        {"driver": "GV6", "value": 0, "uom": 100, "name": "Program"},
    ]


    """
    Commands that this node can handle.
    Should match the 'accepts' section of the nodedef file.
    """
    commands = {
        "QUERY": query,
        "DON": led_on,
        "DOF": led_off,
        "SETRGBW": rgbw_set
    }