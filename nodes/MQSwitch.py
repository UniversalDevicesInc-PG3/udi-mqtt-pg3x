"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy for a generic MQTT switch.

(C) 2025

Node: MQSwitch
"""
import udi_interface
from typing import Optional

LOGGER = udi_interface.LOGGER


class MQSwitch(udi_interface.Node):
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
        payload_upper = payload.upper()
        if payload_upper == "ON":
            self.setDriver("ST", 100)
            if not self.on_state:
                self.reportCmd("DON")
                self.on_state = True
        elif payload_upper == "OFF":
            self.setDriver("ST", 0)
            if self.on_state:
                self.reportCmd("DOF")
                self.on_state = False
        else:
            LOGGER.error(f"Topic: {topic}, Invalid payload: {payload}")
            return
        LOGGER.info(f"Topic: {topic}, Successful payload: {payload}")


    def cmd_on(self, command: dict):
        """
        Handles the 'DON' command from the ISY controller to turn the switch on.

        Args:
            command: The command dictionary from the ISY.
        """
        LOGGER.debug(f"Received ON command: {command}")
        self.controller.mqtt_pub(self.cmd_topic, "ON")


    def cmd_off(self, command: dict):
        """
        Handles the 'DOF' command from the ISY controller to turn the switch off.

        Args:
            command: The command dictionary from the ISY.
        """
        LOGGER.debug(f"Received OFF command: {command}")
        self.controller.mqtt_pub(self.cmd_topic, "OFF")


    def query(self, command: Optional[dict] = None):
        """
        Queries the device for its current state.

        This method is called by the ISY to get the current status of the node.
        It publishes an empty message to the command topic to request a
        status update from the MQTT device and reports all drivers.

        Args:
            command: The command dictionary from the ISY (optional).
        """
        self.controller.mqtt_pub(self.cmd_topic, "")
        self.reportDrivers()


    # For Polyglot internal use. Defines the node's drivers.
    drivers = [
        {"driver": "ST", "value": 0, "uom": 78, "name": "Power"}
    ]

    # For Polyglot internal use. Maps ISY commands to node methods.
    commands = {
        "QUERY": query,
        "DON": cmd_on,
        "DOF": cmd_off
    }

    # For Polyglot UI hint. [type, subtype, major_version, minor_version]
    hint = [4, 2, 0, 0]
