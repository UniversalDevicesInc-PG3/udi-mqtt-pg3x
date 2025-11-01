"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2025

node MQFan
"""

# std libraries
import json

# external libraries
from udi_interface import Node, LOGGER

# personal libraries
pass

# Constants
FAN_OFF = 0
FAN_LOW = 1
FAN_MEDIUM = 2
FAN_HIGH = 3
FAN_MAX = 3


class MQFan(Node):
    """Node representing an MQTT-controlled fan with multiple speeds."""
    id = 'mqfan'

    def __init__(self, polyglot, primary, address, name, device):
        """Initializes the MQFan node.

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
        self.fan_speed = FAN_OFF


    def updateInfo(self, payload: str, topic: str):
        """Updates the fan speed based on a JSON payload from MQTT.

        Args:
            payload: The JSON string received from the MQTT topic.
            topic: The MQTT topic from which the message was received.
        """
        LOGGER.info(f"{self.lpfx} topic:{topic}, payload:{payload}")
        try:
            data = json.loads(payload)
            new_speed = int(data['FanSpeed'])
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            LOGGER.error(f"Could not decode payload or get FanSpeed: {e}")
            return

        if not (FAN_OFF <= new_speed <= FAN_MAX):
            LOGGER.error(f"Received unexpected Fan Speed: {new_speed}")
            return

        if self.fan_speed == FAN_OFF and new_speed > FAN_OFF:
            self.reportCmd("DON")
        elif self.fan_speed > FAN_OFF and new_speed == FAN_OFF:
            self.reportCmd("DOF")
        
        self.fan_speed = new_speed
        self.setDriver("ST", self.fan_speed)
        LOGGER.debug(f"{self.lpfx} Exit")


    def set_on(self, command):
        """Handles the 'DON' command from ISY to set the fan speed."""
        LOGGER.info(f"{self.lpfx} {command}")
        try:
            speed = int(command.get('value'))
        except (ValueError, TypeError, AttributeError):
            LOGGER.warning(f"Invalid or missing speed value in command, defaulting to HIGH: {command}")
            speed = FAN_HIGH

        if not (FAN_OFF <= speed <= FAN_MAX):
            LOGGER.error(f"Received unexpected Fan Speed {speed}, defaulting to HIGH")
            speed = FAN_HIGH
        
        self.fan_speed = speed
        self.setDriver("ST", self.fan_speed)
        self.controller.mqtt_pub(self.cmd_topic, self.fan_speed)
        LOGGER.debug(f"{self.lpfx} Exit")


    def set_off(self, command):
        """Handles the 'DOF' command from ISY to turn the fan off."""
        LOGGER.info(f"{self.lpfx} {command}")
        self.fan_speed = FAN_OFF
        self.setDriver("ST", self.fan_speed)
        self.controller.mqtt_pub(self.cmd_topic, self.fan_speed)
        LOGGER.debug(f"{self.lpfx} Exit")


    def speed_up(self, command):
        """Handles the 'FDUP' command from ISY to increase fan speed."""
        LOGGER.info(f"{self.lpfx} {command}")
        self.controller.mqtt_pub(self.cmd_topic, "+")
        LOGGER.debug(f"{self.lpfx} Exit")


    def speed_down(self, command):
        """Handles the 'FDDOWN' command from ISY to decrease fan speed."""
        LOGGER.info(f"{self.lpfx} {command}")
        self.controller.mqtt_pub(self.cmd_topic, "-")
        LOGGER.debug(f"{self.lpfx} Exit")


    def query(self, command=None):
        """Handles the 'QUERY' command from ISY.

        Requests the current state from the MQTT device.
        """
        LOGGER.info(f"{self.lpfx} {command}")
        self.controller.mqtt_pub(self.cmd_topic, "")
        self.reportDrivers()
        LOGGER.debug(f"{self.lpfx} Exit")


    hint = '0x01040200'
    # home, relay, on/off power strip
    # Hints See: https://github.com/UniversalDevicesInc/hints


    # all the drivers - for reference
    # UOMs of interest:
    # 25: index
    #
    # Driver controls of interest:
    # ST: Status
    drivers = [
        {"driver": "ST", "value": FAN_OFF, "uom": 25, "name": "Power"}
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
