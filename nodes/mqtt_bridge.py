"""MQTT client connection and topic subscription helpers."""

from typing import Iterable, List, Optional

from paho.mqtt.client import Client
from paho.mqtt.enums import CallbackAPIVersion
from udi_interface import LOGGER


class MqttBridge:
    """Wrap paho-mqtt operations used by the Controller."""

    def __init__(self, controller):
        self.controller = controller
        self.client: Optional[Client] = None

    def start(self) -> bool:
        """Start MQTT and retry until the broker becomes available."""
        controller = self.controller
        self.client = Client(CallbackAPIVersion.VERSION1)
        self.client.on_connect = controller._on_connect
        self.client.on_connect_fail = controller._on_connect_fail  # type: ignore
        self.client.on_disconnect = controller._on_disconnect  # type: ignore
        self.client.on_message = controller._on_message
        self.client.username_pw_set(controller.mqtt_user, controller.mqtt_password)
        self.client.reconnect_delay_set(min_delay=2, max_delay=30)
        controller.mqttc = self.client

        controller.Notices["mqtt"] = (
            "Waiting on user MQTT connection; retrying automatically"
        )

        try:
            assert controller.mqtt_server is not None, "mqtt_server must be set"
            assert controller.mqtt_port is not None, "mqtt_port must be set"
            self.client.connect_async(
                controller.mqtt_server,
                controller.mqtt_port,
                keepalive=10,
            )
            self.client.loop_start()
        except Exception as ex:
            LOGGER.exception(f"Unable to start Poly MQTT client: {ex}")
            controller.Notices["mqtt"] = "Error starting user MQTT client"
            return False

        LOGGER.info("MQTT network loop started; automatic reconnect enabled")
        return True

    def publish(self, topic: str, message: str) -> bool:
        if not self.client or not self.client.is_connected():
            LOGGER.warning(
                "MQTT publish rejected while disconnected: topic=%s", topic
            )
            self.controller.Notices["mqtt"] = (
                "User MQTT disconnected; retrying automatically"
            )
            return False

        LOGGER.debug(f"mqtt_pub: topic: {topic}, message: {message}")
        result = self.client.publish(topic, message, retain=False)
        if result.rc != 0:
            LOGGER.error(
                "MQTT publish failed: topic=%s rc=%s", topic, result.rc
            )
            return False
        return True

    def subscribe(
        self,
        topics: Optional[List[str]] = None,
        query_nodes: bool = True,
    ) -> bool:
        controller = self.controller
        if not self.client or not self.client.is_connected():
            return False

        with controller._status_topics_lock:
            topics_to_subscribe = (
                list(topics) if topics is not None else list(controller.status_topics)
            )

        if not topics_to_subscribe:
            return True

        LOGGER.info("Poly MQTT subscribing...")
        results = []
        for stopic in topics_to_subscribe:
            results.append((stopic, tuple(self.client.subscribe(stopic))))

        for topic, (result, mid) in results:
            if result == 0:
                LOGGER.info(f"Subscribed to {topic} MID: {mid}, res: {result}")
            else:
                LOGGER.error(f"Failed to subscribe {topic} MID: {mid}, res: {result}")

        if query_nodes:
            for node in controller.poly.getNodes():
                if node != controller.address:
                    controller.poly.getNode(node).query()
        LOGGER.info("Subscriptions Done")
        return True

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
        self.controller.mqttc = None
