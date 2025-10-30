"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2025

node MQDimmer

Class for a single channel Dimmer.
Currently, supports RJWF-02A
"""

# std libraries
import json

# external libraries
from udi_interface import Node, LOGGER

# personal libraries
pass

# constants
OFF = 0
FULL = 100
INC = 10
DIMLOWERLIMIT = 10 # Dimmer, keep onlevel to a minimum level


class MQDimmer(Node):
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
        self.lpfx = f'{address}:{name}'
        self.cmd_topic = device["cmd_topic"]
        self.status_topic = device["status_topic"]
        self.dimmer = OFF


    def updateInfo(self, payload: str, topic: str):
        """Updates the node's status based on incoming MQTT messages.

        Parses the JSON payload from the device to update the dimmer level and
        power state.

        Args:
            payload: The JSON string received from the MQTT topic.
            topic: The MQTT topic from which the message was received.
        """
        LOGGER.info(f"update:{self.lpfx} topic:{topic}, payload:{payload}")
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
                    new_dimmer = self.dimmer if self.dimmer > OFF else FULL
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
                if self.dimmer == OFF and new_dimmer > OFF:
                    self.reportCmd("DON")
                elif self.dimmer > OFF and new_dimmer == OFF:
                    self.reportCmd("DOF")
                self._set_dimmer_level(new_dimmer, report=False)

        except json.JSONDecodeError as e:
            LOGGER.error(f"Could not decode JSON payload '{payload}': {e}")
        except (ValueError, TypeError) as e:
            LOGGER.error(f"Error processing payload data '{payload}': {e}")
        LOGGER.debug("Exit")


    def _set_dimmer_level(self, level: int, report: bool = True):
        """Sets the dimmer level, updates the driver, and publishes to MQTT.

        Args:
            level: The desired dimmer level (0-100)(OFF-FULL).
            report: If True, sends the command to the MQTT device.
        """
        level = max(OFF, min(FULL, level))  # Clamp level between 0 and 100
        self.dimmer = level
        self.setDriver("ST", self.dimmer)
        if report:
            self.controller.mqtt_pub(self.cmd_topic, self.dimmer)


    def on_cmd(self, command):
        """Handles the 'DON' command from ISY to turn the dimmer on.

        Sets the dimmer to a specified value or a default value if not
        provided.

        Args:
            command: The command object from ISY. Can contain a 'value' key.
        """
        LOGGER.info(f"{self.lpfx}, {command}")
        try:
            level = int(command.get("value", self.dimmer))
        except (ValueError, TypeError):
            LOGGER.warning(
                f"Invalid 'value' in command: {command}. Using last known level."
            )
            level = self.dimmer

        if level == OFF:
            level = INC  # Default to INC(10%) if turning on with a level of OFF(0).
        self._set_dimmer_level(level)
        LOGGER.debug("Exit")


    def off_cmd(self, command):
        """Handles the 'DOF' command from ISY to turn the dimmer off.

        Args:
            command: The command object from ISY.
        """
        LOGGER.info(f"{self.lpfx}, {command}")
        self._set_dimmer_level(OFF)
        LOGGER.debug("Exit")


    def brt_cmd(self, command):
        """Handles the 'BRT' command from ISY to brighten the light.

        Increases the dimmer level by INC.

        Args:
            command: The command object from ISY.
        """
        LOGGER.info(f"{self.lpfx}, {command}")
        new_level = min(self.dimmer + INC, FULL)
        self._set_dimmer_level(new_level)
        LOGGER.debug("Exit")


    def dim_cmd(self, command):
        """Handles the 'DIM' command from ISY to dim the light.

        Decreases the dimmer level by INC.

        Args:
            command: The command object from ISY.
        """
        LOGGER.info(f"{self.lpfx}, {command}")
        new_level = max(self.dimmer - INC, OFF)
        self._set_dimmer_level(new_level)
        LOGGER.debug("Exit")


    def query(self, command=None):
        """Handles the 'QUERY' command from ISY.

        Requests the current state from the MQTT device and reports all drivers.

        Args:
            command: The command object from ISY (optional).
        """
        LOGGER.info(f"{self.lpfx}, {command}")
        query_topic = self.cmd_topic.rsplit("/", 1)[0] + "/State"
        self.controller.mqtt_pub(query_topic, "")
        LOGGER.info(f"Querying device state via topic: {query_topic}")
        self.reportDrivers()
        LOGGER.debug("Exit")


    hint = '0x01020900'
    # home, controller, dimmer switch
    # Hints See: https://github.com/UniversalDevicesInc/hints


    """
    This is an array of dictionary items containing the variable names(drivers)
    values and uoms(units of measure) from ISY. This is how ISY knows what kind
    of variable to display. Check the UOM's in the WSDK for a complete list.
    UOM 2 is boolean so the ISY will display 'True/False'
    """
    drivers = [
        {'driver': 'ST', 'value': OFF, 'uom': 51, 'name': "Status"},
    ]


    """
    This is a dictionary of commands. If ISY sends a command to the NodeServer,
    this tells it which method to call. DON calls setOn, etc.
    """
    commands = {
        "QUERY": query,
        "DON": on_cmd,
        "DOF": off_cmd,
        "BRT": brt_cmd,
        "DIM": dim_cmd,
    }
