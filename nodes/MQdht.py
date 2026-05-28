"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2025

node MQdht

This class adds support for temperature/humidity/Dewpoint sensors.
It was originally developed with an AM2301
"""

from udi_interface import LOGGER

from .MQTasmotaSensor import DEFAULT_SENSOR_ID, MQTasmotaSensor

__all__ = ["MQdht", "DEFAULT_SENSOR_ID"]


class MQdht(MQTasmotaSensor):
    """Node representing a DHT-family environmental sensor."""

    id = "mqdht"

    def __init__(self, polyglot, primary, address, name, device):
        super().__init__(polyglot, primary, address, name)
        self.init_tasmota_device(polyglot, primary, address, name, device)

    def updateInfo(self, payload: str, topic: str):
        """Updates sensor values based on a JSON payload from MQTT."""
        LOGGER.info(f"{self.lpfx} topic:{topic}, payload:{payload}")
        data = self.parse_json_payload(payload)
        if data is None:
            LOGGER.error(f"Could not decode JSON payload '{payload}'")
            return

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
        """Handles the 'QUERY' command from ISY."""
        self.query_tasmota_sensors(command)

    """
    UOMs:
    2: boolean
    17: Fahrenheit (F)
    22: relative humidity

    Driver controls:
    ST: Status (AM2301 ST)
    CLITEMP: Current Temperature (Temperature)
    CLIHUM: Humidity (Humidity)
    DEWPT: Dew Point (Dew Point)
    """
    drivers = [
        {"driver": "ST", "value": 0, "uom": 2, "name": "AM2301 ST"},
        {"driver": "CLITEMP", "value": 0, "uom": 17, "name": "Temperature"},
        {"driver": "CLIHUM", "value": 0, "uom": 22, "name": "Humidity"},
        {"driver": "DEWPT", "value": 0, "uom": 17, "name": "Dew Point"},
    ]

    commands = {
        "QUERY": query,
    }
