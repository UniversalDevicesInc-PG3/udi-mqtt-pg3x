"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2025

node MQs31

Reading the telemetry data for a Sonoff S31 (use the switch for control)
"""

# std libraries
import json

# external libraries
from udi_interface import Node, LOGGER

# personal libraries
pass

# Constants
SENSOR_KEY = "ENERGY"


class MQs31(Node):
    """Node representing a Sonoff S31 Power Monitoring Plug."""

    id = "mqs31"

    def __init__(self, polyglot, primary, address, name, device):
        """Initializes the MQs31 node.

        Args:
            polyglot: Reference to the Polyglot interface.
            primary: The address of the parent node.
            address: The address of this node.
            name: The name of this node.
            device: Dictionary containing device-specific information.
        """
        super().__init__(polyglot, primary, address, name)
        self.lpfx = f"{address}:{name}"

    def updateInfo(self, payload: str, topic: str):
        """Updates all sensor values based on a JSON payload from MQTT."""
        LOGGER.info(f"{self.lpfx} topic:{topic}, payload:{payload}")
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as e:
            LOGGER.error(f"Could not decode JSON payload '{payload}': {e}")
            return

        energy_data = data.get(SENSOR_KEY)
        if isinstance(energy_data, dict):
            self.setDriver("ST", 1)
            self.setDriver("CC", energy_data.get("Current"))
            self.setDriver("CPW", energy_data.get("Power"))
            self.setDriver("CV", energy_data.get("Voltage"))
            self.setDriver("PF", energy_data.get("Factor"))
            self.setDriver("TPW", energy_data.get("Total"))
        else:
            LOGGER.warning(f"Sensor key '{SENSOR_KEY}' not found in payload: {data}")
            self.setDriver("ST", 0)

        LOGGER.debug(f"{self.lpfx} Exit")

    def query(self, command=None):
        """Handles the 'QUERY' command from ISY.

        This is called by ISY to report all drivers for this node.
        """
        LOGGER.info(f"{self.lpfx} {command}")
        self.reportDrivers()
        LOGGER.debug(f"{self.lpfx} Exit")

    """
    UOMs:
    1: ampere (amp)
    2: boolean
    33: kilowatts/hour (kWH)
    53: Power Factor
    72: volt
    73: watt

    Driver controls:
    ST: Status
    CC: Current Current (Current)
    CPW: Current Power Used (Power)
    CV: Current Voltage (Voltage)
    PF: Power Factor (Power Factor)
    TPW: Total Power Used (Total Power)
    """
    drivers = [
        {"driver": "ST", "value": 0, "uom": 2, "name": "Status"},
        {"driver": "CC", "value": 0.00, "uom": 1, "name": "Current"},
        {"driver": "CPW", "value": 0, "uom": 73, "name": "Power"},
        {"driver": "CV", "value": 0, "uom": 72, "name": "Voltage"},
        {"driver": "PF", "value": 0.00, "uom": 53, "name": "Power Factor"},
        {"driver": "TPW", "value": 0.00, "uom": 33, "name": "Total Power"},
    ]

    """
    Commands that this node can handle.
    Should match the 'accepts' section of the nodedef file.
    """
    commands = {
        "QUERY": query,
    }
