"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2025

node MQds

This class is an attempt to add support for temperature only sensors.
was made for DS18B20 waterproof
"""

from udi_interface import LOGGER

from .MQTasmotaSensor import DEFAULT_SENSOR_ID, MQTasmotaSensor

FALLBACK_SENSOR_ID = "DS18B20"

__all__ = ["MQds", "DEFAULT_SENSOR_ID", "FALLBACK_SENSOR_ID"]


class MQds(MQTasmotaSensor):
    """Node representing a DS18B20 temperature sensor."""

    id = "mqds"

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
                LOGGER.warning(
                    f"'Temperature' key not found in sensor data: {sensor_data}"
                )
                self.setDriver("ST", 0)
        else:
            LOGGER.warning(
                f"No valid sensor data found for '{self.sensor_id}' or '{FALLBACK_SENSOR_ID}'"
            )
            self.setDriver("ST", 0)

        LOGGER.debug(f"{self.lpfx} Exit")

    def query(self, command=None):
        """Handles the 'QUERY' command from ISY."""
        self.query_tasmota_sensors(command)

    """
    UOMs:
    2: boolean
    17: Fahrenheit (F)

    Driver controls:
    ST: Status (DS18B20 ST)
    CLITEMP: Current Temperature (Temperature)
    """
    drivers = [
        {"driver": "ST", "value": 0, "uom": 2, "name": "DS18B20 ST"},
        {"driver": "CLITEMP", "value": 0, "uom": 17, "name": "Temperature"},
    ]

    commands = {
        "QUERY": query,
    }
