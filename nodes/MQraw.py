"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2025

node MQraw

This node is for a device that sends a raw integer value.
"""

# std libraries
pass

# external libraries
from udi_interface import Node, LOGGER

# personal libraries
pass


class MQraw(Node):
    """Node representing a device that sends a raw integer value."""
    id = 'mqr'

    def __init__(self, polyglot, primary, address, name, device):
        """Initializes the MQraw node.

        Args:
            polyglot: Reference to the Polyglot interface.
            primary: The address of the parent node.
            address: The address of this node.
            name: The name of this node.
            device: Dictionary containing device-specific information.
        """
        super().__init__(polyglot, primary, address, name)
        self.lpfx = f'{address}:{name}'
        self.cmd_topic = device["cmd_topic"]


    def updateInfo(self, payload: str, topic: str):
        """Updates the node drivers based on a raw payload from MQTT.

        Args:
            payload: The raw string payload received from the MQTT topic.
            topic: The MQTT topic from which the message was received.
        """
        LOGGER.info(f"{self.lpfx} topic:{topic}, payload:{payload}")
        try:
            value = int(payload)
            self.setDriver("ST", 1)
            self.setDriver("GV1", value)
        except ValueError:
            LOGGER.error(f"Failed to parse MQTT Payload as integer: '{payload}'")
            self.setDriver("ST", 0)
            self.setDriver("GV1", 0)
        LOGGER.debug(f"{self.lpfx} Exit")


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
    drivers = [
        {"driver": "ST", "value": 0, "uom": 2},
        {"driver": "GV1", "value": 0, "uom": 56},
    ]


    """
    This is a dictionary of commands. If ISY sends a command to the NodeServer,
    this tells it which method to call. DON calls setOn, etc.
    """
    commands = {
        "QUERY": query,
    }