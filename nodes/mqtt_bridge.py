"""MQTT client connection and topic subscription helpers."""

import time
from typing import Iterable, Optional

from paho.mqtt.client import Client
from paho.mqtt.enums import CallbackAPIVersion
from udi_interface import LOGGER

from .constants import MQTT_CONNECT_WAIT_SEC


class MqttBridge:
    """Wrap paho-mqtt operations used by the Controller."""

    def __init__(self, controller):
        self.controller = controller
        self.client: Optional[Client] = None

    def start(self) -> bool:
        """Connect to the broker and wait up to MQTT_CONNECT_WAIT_SEC."""
        controller = self.controller
        self.client = Client(CallbackAPIVersion.VERSION1)
        self.client.on_connect = controller._on_connect
        self.client.on_disconnect = controller._on_disconnect  # type: ignore
        self.client.on_message = controller._on_message
        self.client.username_pw_set(controller.mqtt_user, controller.mqtt_password)
        controller.mqttc = self.client

        try:
            assert controller.mqtt_server is not None, "mqtt_server must be set"
            assert controller.mqtt_port is not None, "mqtt_port must be set"
            self.client.connect(controller.mqtt_server, controller.mqtt_port, keepalive=10)
            self.client.loop_start()
        except Exception as ex:
            LOGGER.error(f"Error connecting to Poly MQTT broker: {ex}")
            controller.Notices["mqtt"] = "Error on user MQTT connection"
            return False

        deadline = time.time() + MQTT_CONNECT_WAIT_SEC
        while not self.client.is_connected():
            if time.time() >= deadline:
                LOGGER.error(
                    "Timed out waiting for MQTT connection after %s seconds",
                    MQTT_CONNECT_WAIT_SEC,
                )
                controller.Notices["mqtt"] = "Error on user MQTT connection"
                self.client.loop_stop()
                return False
            LOGGER.error("Start: Waiting on user MQTT connection")
            controller.Notices["mqtt"] = "Waiting on user MQTT connection"
            time.sleep(3)

        controller.Notices.clear()
        self.subscribe()
        LOGGER.info("Start Done...")
        return True

    def publish(self, topic: str, message: str) -> None:
        if self.client:
            LOGGER.debug(f"mqtt_pub: topic: {topic}, message: {message}")
            self.client.publish(topic, message, retain=False)

    def subscribe(self) -> None:
        controller = self.controller
        if not self.client:
            return

        LOGGER.info("Poly MQTT subscribing...")
        results = []
        for stopic in controller.status_topics:
            results.append((stopic, tuple(self.client.subscribe(stopic))))

        for topic, (result, mid) in results:
            if result == 0:
                LOGGER.info(f"Subscribed to {topic} MID: {mid}, res: {result}")
            else:
                LOGGER.error(f"Failed to subscribe {topic} MID: {mid}, res: {result}")

        for node in controller.poly.getNodes():
            if node != controller.address:
                controller.poly.getNode(node).query()
        LOGGER.info("Subscriptions Done")

    def unsubscribe(self, topics: Iterable[str]) -> None:
        if not self.client or not self.client.is_connected():
            return

        for topic in topics:
            result, _mid = self.client.unsubscribe(topic)
            if result == 0:
                LOGGER.info(f"Unsubscribed from {topic}")
            else:
                LOGGER.error(f"Failed to unsubscribe {topic}, res: {result}")

    def stop(self) -> None:
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.client = None
