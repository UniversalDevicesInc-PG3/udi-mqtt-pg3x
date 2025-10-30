"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy for a generic MQTT switch.

(C) 2025

Node: MQSwitch
"""

# std libraries
from typing import Optional

# external libraries
from udi_interface import Node, LOGGER

# personal libraries
pass

# constants
OFF = 0
ON = 100
UNKNOWN = 101

class MQSwitch(Node):
    """
    Represents a generic MQTT switch device in the ISY system.

    This node communicates with an MQTT device that accepts "ON" and "OFF"
    payloads to control its state. It reports its power status (On/Off)
    to the ISY controller.
    """
    id = 'MQSW'

    def __init__(self, polyglot, primary: str, address: str, name: str, device: dict):
        """
        Initializes the MQSwitch node.

        Args:
            polyglot: The Polyglot interface instance.
            primary: The address of the parent node.
            address: The address of this node.
            name: The name of this node.
            device: A dictionary containing device-specific information,
                    including the 'cmd_topic' for MQTT communication.
        """
        super().__init__(polyglot, primary, address, name)
        self.controller = self.poly.getNode(self.primary)
        self.cmd_topic = device["cmd_topic"]
        self.on_state = False  # Tracks the on/off state of the switch.
        self.lpfx = f'{address}:{name}'


    def updateInfo(self, payload: str, topic: str):
        """
        Updates the node's state based on incoming MQTT messages.

        This method is called when a message is received on the subscribed
        MQTT topic. It parses the payload and updates the node's 'ST'
        driver, which represents the power state.

        Args:
            payload: The MQTT message payload (e.g., "ON", "OFF").
            topic: The MQTT topic on which the message was received.
        """
        LOGGER.info(f"{self.lpfx} topic:{topic}, payload:{payload}")
        payload_upper = payload.upper()
        if payload_upper == "ON":
            self.setDriver("ST", ON)
            if not self.on_state:
                self.reportCmd("DON")
                self.on_state = True
        elif payload_upper == "OFF":
            self.setDriver("ST", OFF)
            if self.on_state:
                self.reportCmd("DOF")
                self.on_state = False
        else:
            LOGGER.error(f"Topic: {topic}, Invalid payload: {payload}")
            self.setDriver("ST", UNKNOWN)
            return
        LOGGER.debug("Exit")


    def cmd_on(self, command: dict):
        """
        Handles the 'DON' command from the ISY controller to send ON command.
        NOTE: on_state is not changed until received in update.

        Args:
            command: The command dictionary from the ISY.
        """
        LOGGER.info(f"{self.lpfx}, {command}, {self.cmd_topic}")
        self.controller.mqtt_pub(self.cmd_topic, "ON")
        LOGGER.debug("Exit")


    def cmd_off(self, command: dict):
        """
        Handles the 'DOF' command from the ISY controller to send OFF command.
        NOTE: on_state is not changed until received in update.

        Args:
            command: The command dictionary from the ISY.
        """
        LOGGER.info(f"{self.lpfx}, {command}, {self.cmd_topic}")
        self.controller.mqtt_pub(self.cmd_topic, "OFF")
        LOGGER.debug("Exit")


    def query(self, command: Optional[dict] = None):
        """
        Queries the device for its current state.

        This method is called by the ISY to get the current status of the node.
        It publishes an empty message to the command topic to request a
        status update from the MQTT device and reports all drivers.

        Args:
            command: The command dictionary from the ISY (optional).
        """
        LOGGER.info(f"{self.lpfx}, {command}")
        self.controller.mqtt_pub(self.cmd_topic, "")
        self.reportDrivers()
        LOGGER.debug("Exit")


    hint = '0x01040200'
    # home, relay, on/off power strip
    # Hints See: https://github.com/UniversalDevicesInc/hints


    """
    This is an array of dictionary items containing the variable names(drivers)
    values and uoms(units of measure) from ISY. This is how ISY knows what kind
    of variable to display. Check the UOM's in the WSDK for a complete list.
    UOM 2 is boolean so the ISY will display 'True/False'
    """
    drivers = [
        {"driver": "ST", "value": OFF, "uom": 78, "name": "Power"}
    ]

    
    """
    This is a dictionary of commands. If ISY sends a command to the NodeServer,
    this tells it which method to call. DON calls setOn, etc.
    """
    commands = {
        "DON": cmd_on,
        "DOF": cmd_off,
        'QUERY': query,
    }

