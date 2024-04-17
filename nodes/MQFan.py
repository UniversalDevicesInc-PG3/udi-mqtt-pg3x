"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2024

node MQFan
"""

import udi_interface
import json

LOGGER = udi_interface.LOGGER

class MQFan(udi_interface.Node):
    id = 'mqfan'
    
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
        self.fan_speed = 0

    def updateInfo(self, payload, topic: str):
        fan_speed = 0
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
        """
        Called by ISY to report all drivers for this node. This is done in
        the parent class, so you don't need to override this method unless
        there is a need.
        """
        self.controller.mqtt_pub(self.cmd_topic, "")
        self.reportDrivers()
        
    # all the drivers - for reference
    drivers = [
        {"driver": "ST", "value": 0, "uom": 25}
        ]

    """
    This is a dictionary of commands. If ISY sends a command to the NodeServer,
    this tells it which method to call. DON calls setOn, etc.
    """
    commands = {
        "QUERY": query,
        "DON": set_on,
        "DOF": set_off,
        "FDUP": speed_up,
        "FDDOWN": speed_down
    }

    hint = [4, 2, 0, 0]
    
