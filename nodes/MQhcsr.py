"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2025

node MQhcsr

This class is an attempt to add support for HC-SR04 Ultrasonic Sensor.
Returns distance in centimeters.
"""

# std libraries
import json

# external libraries
from udi_interface import Node, LOGGER

# personal libraries
pass

# Constants
SENSOR_KEY = 'SR04'


class MQhcsr(Node):
    """Node representing an HC-SR04 Ultrasonic Distance Sensor."""
    id = 'mqhcsr'

    def __init__(self, polyglot, primary, address, name, device):
        """Initializes the MQhcsr node.

        Args:
            polyglot: Reference to the Polyglot interface.
            primary: The address of the parent node.
            address: The address of this node.
            name: The name of this node.
            device: Dictionary containing device-specific information.
        """
        super().__init__(polyglot, primary, address, name)
        self.lpfx = f'{address}:{name}'


    def updateInfo(self, payload: str, topic: str):
        """Updates sensor value based on a JSON payload from MQTT."""
        LOGGER.info(f"{self.lpfx} topic:{topic}, payload:{payload}")
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as e:
            LOGGER.error(f"Could not decode JSON payload '{payload}': {e}")
            return

        sensor_data = data.get(SENSOR_KEY)
        if isinstance(sensor_data, dict):
            distance = sensor_data.get("Distance")
            if distance is not None:
                self.setDriver("ST", 1)
                self.setDriver("DISTANC", distance)
            else:
                LOGGER.warning(f"'Distance' key not found in sensor data: {sensor_data}")
                self.setDriver("ST", 0)
                self.setDriver("DISTANC", 0)
        else:
            LOGGER.warning(f"Sensor key '{SENSOR_KEY}' not found in payload: {data}")
            self.setDriver("ST", 0)
            self.setDriver("DISTANC", 0)
        
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
    2: boolean
    5: centimeter (cm)

    Driver controls:
    ST: Status
    DISTANC: Distance
    """
    drivers = [
        {"driver": "ST", "value": 0, "uom": 2, "name": "Status"},
        {"driver": "DISTANC", "value": 0, "uom": 5, "name": "Distance"},
    ]


    """
    Commands that this node can handle.
    Should match the 'accepts' section of the nodedef file.
    """
    commands = {
        "QUERY": query,
    }