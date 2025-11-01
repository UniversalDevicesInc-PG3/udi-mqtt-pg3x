"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2025

node MQds

This class is an attempt to add support for temperature only sensors.
was made for DS18B20 waterproof
"""

# std libraries
import json

# external libraries
from udi_interface import Node, LOGGER

# personal libraries
pass

# Constants
DEFAULT_SENSOR_ID = 'SINGLE_SENSOR'
FALLBACK_SENSOR_ID = 'DS18B20'


class MQds(Node):
    """Node representing a DS18B20 temperature sensor."""
    id = 'mqds'

    def __init__(self, polyglot, primary, address, name, device):
        """Initializes the MQds node.

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
        self.sensor_id = device.get('sensor_id', DEFAULT_SENSOR_ID)
        # If sensor_id was not in device, add it for consistency.
        if 'sensor_id' not in device:
            device['sensor_id'] = self.sensor_id


    def updateInfo(self, payload: str, topic: str):
        """Updates sensor values based on a JSON payload from MQTT."""
        LOGGER.info(f"{self.lpfx} topic:{topic}, payload:{payload}")
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as e:
            LOGGER.error(f"Could not decode JSON payload '{payload}': {e}")
            return

        # Handle Tasmota StatusSNS wrapper
        if 'StatusSNS' in data:
            data = data['StatusSNS']

        sensor_data = None
        if self.sensor_id in data:
            sensor_data = data[self.sensor_id]
        elif FALLBACK_SENSOR_ID in data:
            sensor_data = data[FALLBACK_SENSOR_ID]

        if isinstance(sensor_data, dict):
            temp = sensor_data.get("Temperature")
            if temp is not None:
                self.setDriver("ST", 1)
                self.setDriver("CLITEMP", temp)
            else:
                LOGGER.warning(f"'Temperature' key not found in sensor data: {sensor_data}")
                self.setDriver("ST", 0)
        else:
            LOGGER.warning(f"No valid sensor data found for '{self.sensor_id}' or '{FALLBACK_SENSOR_ID}'")
            self.setDriver("ST", 0)
        
        LOGGER.debug(f"{self.lpfx} Exit")


    def query(self, command=None):
        """Handles the 'QUERY' command from ISY.

        Sends a status request to the device.
        """
        LOGGER.info(f"{self.lpfx} {command}")
        # Tasmota: 'Status 10' gets sensor readings
        query_topic = self.cmd_topic.rsplit('/', 1)[0] + '/Status'
        self.controller.mqtt_pub(query_topic, "10")
        LOGGER.debug(f'Query topic: {query_topic}')
        self.reportDrivers()
        LOGGER.debug(f"{self.lpfx} Exit")


    # all the drivers - for reference
    # UOMs of interest:
    # 2: boolean
    # 17: Fahrenheit (F)
    #
    # Driver controls of interest:
    # ST: Status
    # CLITEMP: Current Temperature
    drivers = [
        {"driver": "ST", "value": 0, "uom": 2, "name": "DS18B20 ST"},
        {"driver": "CLITEMP", "value": 0, "uom": 17, "name": "Temperature"},
    ]


    """
    This is a dictionary of commands. If ISY sends a command to the NodeServer,
    this tells it which method to call. DON calls setOn, etc.
    """
    commands = {
        "QUERY": query,
    }