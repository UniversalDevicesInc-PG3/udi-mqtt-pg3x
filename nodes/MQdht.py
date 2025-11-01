"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2025

node MQdht

This class adds support for temperature/humidity/Dewpoint sensors.
It was originally developed with an AM2301
"""

# std libraries
import json

# external libraries
from udi_interface import Node, LOGGER

# personal libraries
pass

# Constants
DEFAULT_SENSOR_ID = 'SINGLE_SENSOR'


class MQdht(Node):
    """Node representing a DHT-family environmental sensor."""
    id = 'mqdht'

    def __init__(self, polyglot, primary, address, name, device):
        """Initializes the MQdht node.

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

        if self.sensor_id in data and isinstance(data[self.sensor_id], dict):
            sensor_data = data[self.sensor_id]
            self.setDriver("ST", 1)
            self.setDriver("CLITEMP", sensor_data.get("Temperature"))
            self.setDriver("CLIHUM", sensor_data.get("Humidity"))
            self.setDriver("DEWPT", sensor_data.get("DewPoint"))
        else:
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
    # 22: relative humidity
    #
    # Driver controls of interest:
    # ST: Status
    # CLITEMP: Current Temperature
    # CLIHUM: Humidity
    # DEWPT: Dew Point
    drivers = [
        {"driver": "ST", "value": 0, "uom": 2, "name": "AM2301 ST"},
        {"driver": "CLITEMP", "value": 0, "uom": 17, "name": "Temperature"},
        {"driver": "CLIHUM", "value": 0, "uom": 22, "name": "Humidity"},
        {"driver": "DEWPT", "value": 0, "uom": 17, "name": "Dew Point"},
        # {"driver": "ERR", "value": 0, "uom": 2}
    ]


    """
    This is a dictionary of commands. If ISY sends a command to the NodeServer,
    this tells it which method to call. DON calls setOn, etc.
    """
    commands = {
        "QUERY": query,
    }