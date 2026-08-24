"""Tests for MqttBridge connection and publish behavior."""

from threading import Lock
from unittest.mock import MagicMock, Mock, patch

import pytest

from nodes.mqtt_bridge import MqttBridge


def _mock_controller():
    controller = Mock()
    controller.mqtt_server = "broker.local"
    controller.mqtt_port = 1883
    controller.mqtt_user = "user"
    controller.mqtt_password = "pass"
    controller.Notices = MagicMock()
    controller._status_topics_lock = Lock()
    controller.status_topics = ["stat/device/POWER"]
    controller.address = "controller"
    controller.poly = Mock()
    controller.poly.getNodes.return_value = {"controller": Mock(), "node1": Mock()}
    controller.poly.getNode.return_value = Mock()
    controller._on_connect = Mock()
    controller._on_connect_fail = Mock()
    controller._on_disconnect = Mock()
    controller._on_message = Mock()
    return controller


class TestMqttBridgeStart:
    @patch("nodes.mqtt_bridge.Client")
    def test_start_uses_async_connect_and_auto_reconnect(self, mock_client_cls):
        controller = _mock_controller()
        client = Mock()
        mock_client_cls.return_value = client

        bridge = MqttBridge(controller)
        assert bridge.start() is True

        client.reconnect_delay_set.assert_called_once_with(min_delay=2, max_delay=30)
        client.connect_async.assert_called_once_with("broker.local", 1883, keepalive=10)
        client.loop_start.assert_called_once()
        assert client.on_connect_fail is controller._on_connect_fail
        assert controller.Notices.__setitem__.call_args_list[0] == (
            ("mqtt", "Waiting on user MQTT connection; retrying automatically"),
        )

    @patch("nodes.mqtt_bridge.Client")
    def test_start_returns_false_when_client_setup_fails(self, mock_client_cls):
        controller = _mock_controller()
        client = Mock()
        client.connect_async.side_effect = OSError("network down")
        mock_client_cls.return_value = client

        bridge = MqttBridge(controller)
        assert bridge.start() is False
        controller.Notices.__setitem__.assert_called_with(
            "mqtt",
            "Error starting user MQTT client",
        )


class TestMqttBridgePublish:
    def test_publish_rejected_when_disconnected(self):
        controller = _mock_controller()
        bridge = MqttBridge(controller)
        bridge.client = Mock()
        bridge.client.is_connected.return_value = False

        assert bridge.publish("cmnd/device/POWER", "ON") is False

        bridge.client.publish.assert_not_called()
        controller.Notices.__setitem__.assert_called_with(
            "mqtt",
            "User MQTT disconnected; retrying automatically",
        )

    def test_publish_succeeds_when_connected(self):
        controller = _mock_controller()
        bridge = MqttBridge(controller)
        bridge.client = Mock()
        bridge.client.is_connected.return_value = True
        publish_result = Mock(rc=0)
        bridge.client.publish.return_value = publish_result

        assert bridge.publish("cmnd/device/POWER", "ON") is True

        bridge.client.publish.assert_called_once_with(
            "cmnd/device/POWER",
            "ON",
            retain=False,
        )

    def test_publish_returns_false_on_nonzero_rc(self):
        controller = _mock_controller()
        bridge = MqttBridge(controller)
        bridge.client = Mock()
        bridge.client.is_connected.return_value = True
        bridge.client.publish.return_value = Mock(rc=4)

        assert bridge.publish("cmnd/device/POWER", "ON") is False


class TestMqttBridgeSubscribe:
    def test_subscribe_snapshots_topics_under_lock(self):
        controller = _mock_controller()
        bridge = MqttBridge(controller)
        bridge.client = Mock()
        bridge.client.is_connected.return_value = True
        bridge.client.subscribe.return_value = (0, 1)

        assert bridge.subscribe(topics=["stat/new/POWER"], query_nodes=False) is True

        bridge.client.subscribe.assert_called_once_with("stat/new/POWER")
        controller.poly.getNode.assert_not_called()

    def test_subscribe_queries_nodes_on_initial_connect(self):
        controller = _mock_controller()
        bridge = MqttBridge(controller)
        bridge.client = Mock()
        bridge.client.is_connected.return_value = True
        bridge.client.subscribe.return_value = (0, 1)
        mock_node = Mock()
        controller.poly.getNode.return_value = mock_node

        assert bridge.subscribe(query_nodes=True) is True

        mock_node.query.assert_called_once()

    def test_subscribe_skipped_when_disconnected(self):
        controller = _mock_controller()
        bridge = MqttBridge(controller)
        bridge.client = Mock()
        bridge.client.is_connected.return_value = False

        assert bridge.subscribe() is False


class TestMqttBridgeStop:
    def test_stop_clears_controller_mqttc(self):
        controller = _mock_controller()
        bridge = MqttBridge(controller)
        client = Mock()
        bridge.client = client
        controller.mqttc = client

        bridge.stop()

        client.loop_stop.assert_called_once()
        client.disconnect.assert_called_once()
        assert bridge.client is None
        assert controller.mqttc is None
