"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2025

node MQAnalog

General purpose Analog input using ADC.
"""

from udi_interface import LOGGER

from .MQTasmotaSensor import DEFAULT_SENSOR_ID, MQTasmotaSensor

__all__ = ["MQAnalog", "DEFAULT_SENSOR_ID"]


class MQAnalog(MQTasmotaSensor):
    """Node representing a generic analog sensor from an MQTT device."""

    id = "mqanal"

    def __init__(self, polyglot, primary, address, name, device):
        super().__init__(polyglot, primary, address, name)
        self.init_tasmota_device(polyglot, primary, address, name, device)

    def updateInfo(self, payload: str, topic: str):
        """Updates the analog sensor value based on a JSON payload from MQTT."""
        LOGGER.info(f"{self.lpfx} topic:{topic}, payload:{payload}")
        data = self.parse_json_payload(payload)
        if data is None:
            LOGGER.error(f"Could not decode JSON payload '{payload}'")
            return

        self._process_analog_data(data)
        LOGGER.debug(f"{self.lpfx} Exit")

    def _process_analog_data(self, data: dict):
        """Parses the data dictionary for ANALOG readings and updates drivers."""
        if "ANALOG" not in data or not isinstance(data["ANALOG"], dict):
            LOGGER.debug(f"No ANALOG data found in payload: {data}")
            self.setDriver("ST", 0)
            self.setDriver("GPV", 0)
            return

        self.setDriver("ST", 1)
        analog_data = data["ANALOG"]

        if self.sensor_id != DEFAULT_SENSOR_ID:
            try:
                value = analog_data[self.sensor_id]
                self.setDriver("GPV", value)
                LOGGER.info(f"Multi-sensor analog {self.sensor_id}: {value}")
            except KeyError:
                LOGGER.error(
                    f'Sensor ID "{self.sensor_id}" not found in ANALOG payload: {analog_data}'
                )
        else:
            try:
                key, value = next(iter(analog_data.items()))
                self.setDriver("GPV", value)
                LOGGER.info(f"Single-sensor analog {key}: {value}")
            except StopIteration:
                LOGGER.error(
                    f"ANALOG data is empty, cannot read single sensor value: {analog_data}"
                )

    def query(self, command=None):
        """Handles the 'QUERY' command from ISY."""
        self.query_tasmota_sensors(command)

    """
    UOMs:
    2: boolean
    56: The raw value as reported by the device

    Driver controls:
    ST: Status (Analog ST)
    GPV: General Purpose Value (Analog)
    """
    drivers = [
        {"driver": "ST", "value": 0, "uom": 2, "name": "Analog ST"},
        {"driver": "GPV", "value": 0, "uom": 56, "name": "Analog"},
    ]

    commands = {
        "QUERY": query,
    }
