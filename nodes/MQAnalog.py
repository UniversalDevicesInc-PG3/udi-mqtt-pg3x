"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2025

node MQAnalog

General purpose Analog input using ADC.
"""

# std libraries
import json

# external libraries
from udi_interface import Node, LOGGER

# personal libraries
pass

# Constants
DEFAULT_SENSOR_ID = 'SINGLE_SENSOR'


class MQAnalog(Node):
    """Node representing a generic analog sensor from an MQTT device."""
    id = 'mqanal'

    def __init__(self, polyglot, primary, address, name, device):
        """Initializes the MQAnalog node.

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


    def updateInfo(self, payload: str, topic: str):
        """Updates the analog sensor value based on a JSON payload from MQTT.

        Args:
            payload: The JSON string received from the MQTT topic.
            topic: The MQTT topic from which the message was received.
        """
        LOGGER.info(f"{self.lpfx} topic:{topic}, payload:{payload}")
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as e:
            LOGGER.error(f"Could not decode JSON payload '{payload}': {e}")
            return

        # Handle Tasmota StatusSNS wrapper
        if 'StatusSNS' in data:
            data = data['StatusSNS']

        self._process_analog_data(data)
        LOGGER.debug(f"{self.lpfx} Exit")


    def _process_analog_data(self, data: dict):
        """Parses the data dictionary for ANALOG readings and updates drivers."""
        if "ANALOG" not in data or not isinstance(data["ANALOG"], dict):
            LOGGER.debug(f'No ANALOG data found in payload: {data}')
            self.setDriver("ST", 0)
            self.setDriver("GPV", 0)
            return

        self.setDriver("ST", 1)
        analog_data = data["ANALOG"]

        if self.sensor_id != DEFAULT_SENSOR_ID:
            try:
                value = analog_data[self.sensor_id]
                self.setDriver("GPV", value)
                LOGGER.info(f'Multi-sensor analog {self.sensor_id}: {value}')
            except KeyError:
                LOGGER.error(f'Sensor ID "{self.sensor_id}" not found in ANALOG payload: {analog_data}')
        else:
            try:
                # Assumes there is only one key-value pair for a single sensor device
                key, value = next(iter(analog_data.items()))
                self.setDriver("GPV", value)
                LOGGER.info(f'Single-sensor analog {key}: {value}')
            except StopIteration:
                LOGGER.error(f'ANALOG data is empty, cannot read single sensor value: {analog_data}')


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
    # 56: The raw value as reported by the device
    #
    # Driver controls of interest:
    # ST: Status
    # GPV: General Purpose Value
    drivers = [
        {"driver": "ST", "value": 0, "uom": 2, "name": "Analog ST"},
        {"driver": "GPV", "value": 0, "uom": 56, "name": "Analog"}
    ]


    """
    This is a dictionary of commands. If ISY sends a command to the NodeServer,
    this tells it which method to call. DON calls setOn, etc.
    """
    commands = {
        "QUERY": query,
    }