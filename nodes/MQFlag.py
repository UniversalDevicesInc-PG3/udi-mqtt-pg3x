"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2025

node MQFlag

This node is intended as a flag for a sensor or condition on an IoT device,
allowing the device program, rather than the ISY, to control the state.

FLAG-0 = OK
FLAG-1 = NOK
FLAG-2 = LO
FLAG-3 = HI
FLAG-4 = ERR
FLAG-5 = IN
FLAG-6 = OUT
FLAG-7 = UP
FLAG-8 = DOWN
FLAG-9 = TRIGGER
FLAG-10 = ON
FLAG-11 = OFF
FLAG-12 = ---

Payload is direct (like a switch) not JSON encoded (like a sensor).
Example device: liquid float {OK, LO, HI}
Example condition: IOT device sensor connections {OK, NOK, ERR(OR)}
"""

# external libraries
from udi_interface import Node, LOGGER

# Constants
PAYLOAD_MAP = {
    "OK": 0,
    "NOK": 1,
    "LO": 2,
    "HI": 3,
    "ERR": 4,
    "IN": 5,
    "OUT": 6,
    "UP": 7,
    "DOWN": 8,
    "TRIGGER": 9,
    "ON": 10,
    "OFF": 11,
    "---": 12,
}
ERROR_STATE = PAYLOAD_MAP["ERR"]


class MQFlag(Node):
    """Node representing a generic flag or state from an MQTT device.

    This class receives simple string payloads (e.g., "OK", "ERR") from an
    MQTT topic and maps them to a numerical state in the Polisy/ISY system.
    """

    id = "mqflag"

    def __init__(self, polyglot, primary, address, name, device):
        """Initializes the MQFlag node.

        Args:
            polyglot: Reference to the Polyglot interface.
            primary: The address of the parent node.
            address: The address of this node.
            name: The name of this node.
            device: Dictionary containing device-specific information.
        """
        super().__init__(polyglot, primary, address, name)
        self.controller = self.poly.getNode(self.primary)
        self.lpfx = f"{address}:{name}"
        self.cmd_topic = device["cmd_topic"]

    def updateInfo(self, payload, topic: str):
        """Updates the node's status based on incoming MQTT messages.

        Args:
            payload: The string payload received from the MQTT topic.
            topic: The MQTT topic from which the message was received.
        """
        LOGGER.info(f"{self.lpfx} topic:{topic}, payload:{payload}")
        state = PAYLOAD_MAP.get(payload)

        if state is None:
            LOGGER.error(f"Invalid payload received: {payload}")
            state = ERROR_STATE

        self.setDriver("ST", state)
        self.reportCmd("DON")  # report Setting, can be used in scenes
        LOGGER.debug(f"{self.lpfx} Exit")

    def reset_send(self, command):
        """Handles the 'RESET' command from ISY.

        Publishes 'RESET' to the command topic.

        Args:
            command: The command object from ISY.
        """
        LOGGER.info(f"{self.lpfx} {command}, {self.cmd_topic}")
        self.controller.mqtt_pub(self.cmd_topic, "RESET")
        self.reportCmd("DOF")  # report Resetting, can be used in scenes
        LOGGER.debug(f"{self.lpfx} Exit")

    def query(self, command=None):
        """Handles the 'QUERY' command from ISY.

        Requests the current state from the MQTT device and reports all drivers.

        Args:
            command: The command object from ISY (optional).
        """
        LOGGER.info(f"{self.lpfx} {command}")
        self.controller.mqtt_pub(self.cmd_topic, "")
        self.reportDrivers()
        LOGGER.debug(f"{self.lpfx} Exit")

    hint = "0x01010000"
    # home, alarm, none
    # Hints See: https://github.com/UniversalDevicesInc/hints

    """
    UOMs:
    25: index

    Driver controls:
    ST: Status
    """
    drivers = [{"driver": "ST", "value": 0, "uom": 25, "name": "Status"}]

    """
    Commands that this node can handle.
    Should match the 'accepts' section of the nodedef file.
    """
    commands = {"QUERY": query, "RESET": reset_send}
