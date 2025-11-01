"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2024

node MQRGBWstrip

Class for an RGBW strip powered through a microController running MQTT client
able to set colours and run different transition programs
"""

import udi_interface
import json

LOGGER = udi_interface.LOGGER

class MQRGBWstrip(udi_interface.Node):
    id = 'mqrgbw'
    
    """
    This is the class that all the Nodes will be represented by. You will
    add this to Polyglot/ISY with the interface.addNode method.
    """
    def __init__(self, polyglot, primary, address, name, device):
        """
        Super runs all the parent class necessities.
        :param polyglot: Reference to the Interface class
        :param primary: Parent address
        :param address: This nodes address
        :param name: This nodes name
        """
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
        """
        Called by ISY to report all drivers for this node. This is done in
        the parent class, so you don't need to override this method unless
        there is a need.
        """
        self.reportDrivers()
        
    # UOMs of interest:
    # 2: boolean
    # 78: 0-Off 100-On, 101-Unknown
    # 100: A Level from 0-255
    #
    # Driver controls of interest:
    # ST: Status
    # GV0: Custom Control 0
    # GV1: Custom Control 1
    # GV2: Custom Control 2
    # GV3: Custom Control 3
    # GV4: Custom Control 4
    # GV5: Custom Control 5
    # GV6: Custom Control 6
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

    """
    This is a dictionary of commands. If ISY sends a command to the NodeServer,
    this tells it which method to call. DON calls setOn, etc.
    """
    commands = {
        "QUERY": query,
        "DON": led_on,
        "DOF": led_off,
        "SETRGBW": rgbw_set
    }


