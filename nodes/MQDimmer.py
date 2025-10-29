"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2024

node MQDimmer

Class for a single channel Dimmer.
Currently, supports RJWF-02A
"""

import json

import udi_interface

LOGGER = udi_interface.LOGGER


class MQDimmer(udi_interface.Node):
    """Node representing a single-channel MQTT-controlled dimmer.

    This class handles communication with an MQTT dimmer device, allowing for
    on/off control, brightness adjustments, and status reporting to the
    Polisy/ISY system.
    """

    id = "mqdimmer"

    def __init__(self, polyglot, primary, address, name, device):
        """Initializes the MQDimmer node.

        Args:
            polyglot: Reference to the Polyglot interface.
            primary: The address of the parent node.
            address: The address of this node.
            name: The name of this node.
            device: Dictionary containing device-specific information, including
                    'cmd_topic' and 'status_topic'.
        """
        super().__init__(polyglot, primary, address, name)
        self.controller = self.poly.getNode(self.primary)
        self.cmd_topic = device["cmd_topic"]
        self.status_topic = device["status_topic"]
        self.dimmer = 0


    def updateInfo(self, payload: str, topic: str):
        """Updates the node's status based on incoming MQTT messages.

        Parses the JSON payload from the device to update the dimmer level and
        power state.

        Args:
            payload: The JSON string received from the MQTT topic.
            topic: The MQTT topic from which the message was received.
        """
        try:
            data = json.loads(payload)
            power = data.get("POWER")
            new_dimmer = data.get("Dimmer")

            if new_dimmer is not None:
                new_dimmer = int(new_dimmer)

            LOGGER.info(f"Received update: Dimmer={new_dimmer}, Power={power}")

            # If power state is provided, it takes precedence.
            if power == "ON":
                # If dimmer level is not specified on "ON", we might need to assume a level.
                # Here we use the last known dimmer level if it was > 0, otherwise default to 100.
                if new_dimmer is None:
                    new_dimmer = self.dimmer if self.dimmer > 0 else 100
                self.reportCmd("DON")
                self._set_dimmer_level(
                    new_dimmer, report=False
                )  # report=False to avoid double reporting DON
            elif power == "OFF":
                self.reportCmd("DOF")
                self._set_dimmer_level(
                    0, report=False
                )  # report=False to avoid double reporting DOF

            # If only dimmer level is provided
            elif new_dimmer is not None:
                if self.dimmer == 0 and new_dimmer > 0:
                    self.reportCmd("DON")
                elif self.dimmer > 0 and new_dimmer == 0:
                    self.reportCmd("DOF")
                self._set_dimmer_level(new_dimmer, report=False)

        except json.JSONDecodeError as e:
            LOGGER.error(f"Could not decode JSON payload '{payload}': {e}")
        except (ValueError, TypeError) as e:
            LOGGER.error(f"Error processing payload data '{payload}': {e}")


    def _set_dimmer_level(self, level: int, report: bool = True):
        """Sets the dimmer level, updates the driver, and publishes to MQTT.

        Args:
            level: The desired dimmer level (0-100).
            report: If True, sends the command to the MQTT device.
        """
        level = max(0, min(100, level))  # Clamp level between 0 and 100
        self.dimmer = level
        self.setDriver("ST", self.dimmer)
        if report:
            self.controller.mqtt_pub(self.cmd_topic, self.dimmer)


    def set_on(self, command):
        """Handles the 'DON' command from ISY to turn the dimmer on.

        Sets the dimmer to a specified value or a default value if not
        provided.

        Args:
            command: The command object from ISY. Can contain a 'value' key.
        """
        try:
            level = int(command.get("value", self.dimmer))
        except (ValueError, TypeError):
            LOGGER.warning(
                f"Invalid 'value' in command: {command}. Using last known level."
            )
            level = self.dimmer

        if level == 0:
            level = 10  # Default to 10% if turning on with a level of 0.
        self._set_dimmer_level(level)


    def set_off(self, command):
        """Handles the 'DOF' command from ISY to turn the dimmer off.

        Args:
            command: The command object from ISY.
        """
        self._set_dimmer_level(0)


    def brighten(self, command):
        """Handles the 'BRT' command from ISY to brighten the light.

        Increases the dimmer level by 10%.

        Args:
            command: The command object from ISY.
        """
        new_level = self.dimmer + 10
        self._set_dimmer_level(new_level)


    def dim(self, command):
        """Handles the 'DIM' command from ISY to dim the light.

        Decreases the dimmer level by 10%.

        Args:
            command: The command object from ISY.
        """
        new_level = self.dimmer - 10
        self._set_dimmer_level(new_level)


    def query(self, command=None):
        """Handles the 'QUERY' command from ISY.

        Requests the current state from the MQTT device and reports all drivers.

        Args:
            command: The command object from ISY (optional).
        """
        query_topic = self.cmd_topic.rsplit("/", 1)[0] + "/State"
        self.controller.mqtt_pub(query_topic, "")
        LOGGER.info(f"Querying device state via topic: {query_topic}")
        self.reportDrivers()


    # all the drivers - for reference
    drivers = [{"driver": "ST", "value": 0, "uom": 51, "name": "Status"}]


    """
    This is a dictionary of commands. If ISY sends a command to the NodeServer,
    this tells it which method to call. DON calls setOn, etc.
    """
    commands = {
        "QUERY": query,
        "DON": set_on,
        "DOF": set_off,
        "BRT": brighten,
        "DIM": dim,
    }


    hint = [1, 2, 9, 0]