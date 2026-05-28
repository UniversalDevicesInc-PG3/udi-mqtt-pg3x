"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2025

node MQbme

This class is an attempt to add support for temperature/humidity/pressure sensors.
Currently, supports the BME280. Could be extended to accept others.
"""

from udi_interface import LOGGER

from .MQTasmotaSensor import DEFAULT_SENSOR_ID, MQTasmotaSensor

__all__ = ["MQbme", "HPA_TO_INHG", "DEFAULT_SENSOR_ID"]

HPA_TO_INHG = 0.02952998751


class MQbme(MQTasmotaSensor):
    """Node representing a BME280 environmental sensor."""

    id = "mqbme"

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

            if "Pressure" in sensor_data:
                pressure_hg = self._convert_pressure(sensor_data["Pressure"])
                if pressure_hg is not None:
                    self.setDriver("BARPRES", pressure_hg)
        else:
            self.setDriver("ST", 0)

        LOGGER.debug(f"{self.lpfx} Exit")

    def _convert_pressure(self, hpa_pressure) -> float | None:
        """Converts pressure from hPa to inHg."""
        try:
            return round(float(hpa_pressure) * HPA_TO_INHG, 2)
        except (ValueError, TypeError) as e:
            LOGGER.error(f"Could not convert pressure value '{hpa_pressure}': {e}")
            return None

    def query(self, command=None):
        """Handles the 'QUERY' command from ISY."""
        self.query_tasmota_sensors(command)

    """
    UOMs:
    2: boolean
    17: Fahrenheit (F)
    22: relative humidity
    23: inches of mercury (inHg)

    Driver controls:
    ST: Status (Status)
    CLITEMP: Current Temperature (Temperature)
    CLIHUM: Humidity (Humidity)
    DEWPT: Dew Point (Dew Point)
    BARPRES: Barometric Pressure (Barometric Pressure)
    """
    drivers = [
        {"driver": "ST", "value": 0, "uom": 2, "name": "Status"},
        {"driver": "CLITEMP", "value": 0, "uom": 17, "name": "Temperature"},
        {"driver": "CLIHUM", "value": 0, "uom": 22, "name": "Humidity"},
        {"driver": "DEWPT", "value": 0, "uom": 17, "name": "Dew Point"},
        {"driver": "BARPRES", "value": 0, "uom": 23, "name": "Barometric Pressure"},
    ]

    commands = {
        "QUERY": query,
    }
