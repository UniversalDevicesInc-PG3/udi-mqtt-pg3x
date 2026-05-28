"""Base class for Tasmota SENSOR/StatusSNS device nodes."""

import json
from typing import Any, Dict, Optional

from udi_interface import Node, LOGGER

DEFAULT_SENSOR_ID = "SINGLE_SENSOR"


class MQTasmotaSensor(Node):
    """Shared helpers for Tasmota JSON sensor payloads."""

    def init_tasmota_device(
        self,
        polyglot,
        primary: str,
        address: str,
        name: str,
        device: dict,
        default_sensor_id: str = DEFAULT_SENSOR_ID,
    ) -> None:
        self.controller = self.poly.getNode(self.primary)
        self.lpfx = f"{address}:{name}"
        self.cmd_topic = device["cmd_topic"]
        self.sensor_id = device.get("sensor_id", default_sensor_id)
        if "sensor_id" not in device:
            device["sensor_id"] = self.sensor_id

    @staticmethod
    def parse_json_payload(payload: str) -> Optional[Dict[str, Any]]:
        """Parse normalized MQTT JSON payload from the Controller."""
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        return data

    def query_tasmota_sensors(self, command=None) -> None:
        """Request Tasmota Status 10 sensor readings."""
        LOGGER.info(f"{self.lpfx} {command}")
        query_topic = self.cmd_topic.rsplit("/", 1)[0] + "/Status"
        self.controller.mqtt_pub(query_topic, "10")
        LOGGER.debug(f"Query topic: {query_topic}")
        self.reportDrivers()
        LOGGER.debug(f"{self.lpfx} Exit")
