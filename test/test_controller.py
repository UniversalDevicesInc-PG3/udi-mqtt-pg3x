"""
Comprehensive test suite for Controller node.

Tests cover:
- Initialization and setup
- Configuration loading (devfile, devlist, MQTT parameters)
- Device discovery and node creation
- MQTT connection management
- Status topic management
- Node lifecycle (add/remove)
- Event handlers
- Helper methods
"""

import pytest
from unittest.mock import Mock, patch
from nodes.Controller import (
    Controller,
    DEFAULT_CONFIG,
    STATUS_TOPIC_PREFIX,
    TELE_TOPIC_PREFIX,
    RESULT_TOPIC_SUFFIX,
    STATUS10_TOPIC_SUFFIX,
    SENSOR_PROCESSORS,
    DEVICE_CONFIG,
)


class TestControllerInitialization:
    """Tests for Controller initialization."""

    @pytest.fixture
    def mock_polyglot(self):
        """Create a mock polyglot interface."""
        poly = Mock()
        poly.START = "START"
        poly.POLL = "POLL"
        poly.LOGLEVEL = "LOGLEVEL"
        poly.CUSTOMPARAMS = "CUSTOMPARAMS"
        poly.CUSTOMDATA = "CUSTOMDATA"
        poly.STOP = "STOP"
        poly.DISCOVER = "DISCOVER"
        poly.CUSTOMTYPEDDATA = "CUSTOMTYPEDDATA"
        poly.CUSTOMTYPEDPARAMS = "CUSTOMTYPEDPARAMS"
        poly.ADDNODEDONE = "ADDNODEDONE"
        poly.subscribe = Mock()
        poly.ready = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        return poly

    def test_initialization_basic(self, mock_polyglot):
        """Test basic Controller initialization."""
        controller = Controller(mock_polyglot, "controller", "controller", "MQTT")

        assert controller.id == "mqctrl"
        assert controller.address == "controller"
        assert controller.name == "MQTT"
        assert controller.hb == 0
        assert controller.numNodes == 0
        assert controller.devlist == []
        assert controller.status_topics == []
        assert controller.valid_configuration is False
        assert controller.discovery_in is False

    def test_initialization_subscribes_to_events(self, mock_polyglot):
        """Test that initialization subscribes to all required events."""
        Controller(mock_polyglot, "controller", "controller", "MQTT")

        # Verify all subscriptions
        subscribe_calls = mock_polyglot.subscribe.call_args_list
        assert len(subscribe_calls) == 10

        # Check specific subscriptions
        event_types = [call[0][0] for call in subscribe_calls]
        assert "START" in event_types
        assert "POLL" in event_types
        assert "LOGLEVEL" in event_types
        assert "CUSTOMPARAMS" in event_types
        assert "CUSTOMDATA" in event_types
        assert "STOP" in event_types
        assert "DISCOVER" in event_types

    def test_initialization_calls_ready(self, mock_polyglot):
        """Test that initialization calls poly.ready()."""
        Controller(mock_polyglot, "controller", "controller", "MQTT")

        mock_polyglot.ready.assert_called_once()


class TestControllerConstants:
    """Tests for module constants."""

    def test_default_config(self):
        """Test default configuration values."""
        assert DEFAULT_CONFIG["mqtt_server"] == "localhost"
        assert DEFAULT_CONFIG["mqtt_port"] == 1884
        assert DEFAULT_CONFIG["mqtt_user"] == "admin"
        assert DEFAULT_CONFIG["mqtt_password"] == "admin"
        assert DEFAULT_CONFIG["status_prefix"] is None
        assert DEFAULT_CONFIG["cmd_prefix"] is None

    def test_topic_constants(self):
        """Test MQTT topic constants."""
        assert STATUS_TOPIC_PREFIX == "stat/"
        assert TELE_TOPIC_PREFIX == "tele/"
        assert RESULT_TOPIC_SUFFIX == "/RESULT"
        assert STATUS10_TOPIC_SUFFIX == "/STATUS10"

    def test_sensor_processors(self):
        """Test sensor processor mapping."""
        assert "ANALOG" in SENSOR_PROCESSORS
        assert "DS18B20" in SENSOR_PROCESSORS
        assert "AM2301" in SENSOR_PROCESSORS
        assert "BME280" in SENSOR_PROCESSORS

    def test_device_config_has_all_types(self):
        """Test that DEVICE_CONFIG includes all device types."""
        expected_types = [
            "switch",
            "dimmer",
            "ifan",
            "sensor",
            "flag",
            "TempHumid",
            "Temp",
            "TempHumidPress",
            "distance",
            "shellyflood",
            "analog",
            "s31",
            "raw",
            "RGBW",
            "ratgdo",
        ]
        for dev_type in expected_types:
            assert dev_type in DEVICE_CONFIG


class TestControllerUpsertById:
    """Tests for upsert_by_id method."""

    @pytest.fixture
    def controller(self):
        """Create a Controller instance for testing."""
        poly = Mock()
        poly.subscribe = Mock()
        poly.ready = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        for attr in [
            "START",
            "POLL",
            "LOGLEVEL",
            "CUSTOMPARAMS",
            "CUSTOMDATA",
            "STOP",
            "DISCOVER",
            "CUSTOMTYPEDDATA",
            "CUSTOMTYPEDPARAMS",
            "ADDNODEDONE",
        ]:
            setattr(poly, attr, attr)

        c = Controller(poly, "controller", "controller", "MQTT")
        return c

    def test_upsert_adds_new_entry(self, controller):
        """Test upserting a new entry to an empty list."""
        config_list = []
        new_entry = {"id": "device1", "type": "switch"}

        controller.upsert_by_id(config_list, new_entry)

        assert len(config_list) == 1
        assert config_list[0] == new_entry

    def test_upsert_updates_existing_entry(self, controller):
        """Test upserting an existing entry."""
        config_list = [
            {"id": "device1", "type": "switch", "enabled": True},
            {"id": "device2", "type": "dimmer"},
        ]
        new_entry = {"id": "device1", "type": "switch", "enabled": False}

        controller.upsert_by_id(config_list, new_entry)

        assert len(config_list) == 2
        assert config_list[0]["enabled"] is False

    def test_upsert_preserves_other_entries(self, controller):
        """Test that upsert preserves other entries."""
        config_list = [
            {"id": "device1", "type": "switch"},
            {"id": "device2", "type": "dimmer"},
        ]
        new_entry = {"id": "device3", "type": "sensor"}

        controller.upsert_by_id(config_list, new_entry)

        assert len(config_list) == 3
        assert config_list[0]["id"] == "device1"
        assert config_list[1]["id"] == "device2"
        assert config_list[2]["id"] == "device3"


class TestControllerGetHelpers:
    """Tests for _get_str and _get_int helper methods."""

    def test_get_str_with_valid_string(self):
        """Test _get_str with a valid string."""
        result = Controller._get_str("test_value")
        assert result == "test_value"

    def test_get_str_with_none(self):
        """Test _get_str with None."""
        result = Controller._get_str(None)
        assert result is None

    def test_get_str_with_empty_string(self):
        """Test _get_str with empty string."""
        result = Controller._get_str("")
        assert result == ""

    def test_get_str_with_whitespace(self):
        """Test _get_str with whitespace."""
        result = Controller._get_str("   ")
        assert result == "   "

    def test_get_str_with_multiple_args(self):
        """Test _get_str with multiple arguments."""
        result = Controller._get_str(None, 42, "test", "other")
        assert result == "test"

    def test_get_int_with_valid_int(self):
        """Test _get_int with a valid integer."""
        result = Controller._get_int(42)
        assert result == 42

    def test_get_int_with_string_number(self):
        """Test _get_int with string number."""
        result = Controller._get_int("42")
        assert result == 42

    def test_get_int_with_none(self):
        """Test _get_int with None."""
        result = Controller._get_int(None)
        assert result is None

    def test_get_int_with_invalid_string(self):
        """Test _get_int with invalid string."""
        result = Controller._get_int("not_a_number")
        assert result is None

    def test_get_int_with_empty_string(self):
        """Test _get_int with empty string."""
        result = Controller._get_int("")
        assert result is None


class TestControllerNormalizeTopic:
    """Tests for _normalize_topic method."""

    @pytest.fixture
    def controller(self):
        """Create a Controller instance for testing."""
        poly = Mock()
        poly.subscribe = Mock()
        poly.ready = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        for attr in [
            "START",
            "POLL",
            "LOGLEVEL",
            "CUSTOMPARAMS",
            "CUSTOMDATA",
            "STOP",
            "DISCOVER",
            "CUSTOMTYPEDDATA",
            "CUSTOMTYPEDPARAMS",
            "ADDNODEDONE",
        ]:
            setattr(poly, attr, attr)

        c = Controller(poly, "controller", "controller", "MQTT")
        return c

    def test_normalize_topic_without_prefix(self, controller):
        """Test normalizing topic without prefix."""
        result = controller._normalize_topic("~/device/topic", None)
        # Without prefix, ~ remains
        assert result == "~/device/topic"

    def test_normalize_topic_with_prefix(self, controller):
        """Test normalizing topic with prefix (replaces ~)."""
        result = controller._normalize_topic("~device/topic", "stat/")
        assert result == "stat/device/topic"

    def test_normalize_topic_without_tilde(self, controller):
        """Test normalizing topic without tilde placeholder."""
        result = controller._normalize_topic("device/topic", "stat/")
        # Without ~, prefix is not added
        assert result == "device/topic"

    def test_normalize_topic_already_has_prefix(self, controller):
        """Test normalizing topic that already has prefix."""
        result = controller._normalize_topic("stat/device/topic", "stat/")
        assert result == "stat/device/topic"

    def test_normalize_topic_with_none_topic(self, controller):
        """Test normalizing None topic."""
        result = controller._normalize_topic(None, "stat/")
        assert result == ""

    def test_normalize_topic_with_empty_topic(self, controller):
        """Test normalizing empty topic."""
        result = controller._normalize_topic("", "stat/")
        assert result == ""


class TestControllerValidateDeviceDefinition:
    """Tests for _validate_device_definition method."""

    @pytest.fixture
    def controller(self):
        """Create a Controller instance for testing."""
        poly = Mock()
        poly.subscribe = Mock()
        poly.ready = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        for attr in [
            "START",
            "POLL",
            "LOGLEVEL",
            "CUSTOMPARAMS",
            "CUSTOMDATA",
            "STOP",
            "DISCOVER",
            "CUSTOMTYPEDDATA",
            "CUSTOMTYPEDPARAMS",
            "ADDNODEDONE",
        ]:
            setattr(poly, attr, attr)

        c = Controller(poly, "controller", "controller", "MQTT")
        return c

    def test_validate_valid_device(self, controller):
        """Test validating a valid device definition."""
        dev = {
            "id": "device1",
            "type": "switch",
            "status_topic": "stat/device1/POWER",
            "cmd_topic": "cmnd/device1/POWER",
        }

        is_valid = controller._validate_device_definition(dev)

        assert is_valid is True

    def test_validate_device_missing_id(self, controller):
        """Test validating device without id."""
        dev = {
            "type": "switch",
            "status_topic": "stat/device/POWER",
            "cmd_topic": "cmnd/device/POWER",
        }

        is_valid = controller._validate_device_definition(dev)

        assert is_valid is False

    def test_validate_device_missing_type(self, controller):
        """Test validating device without type."""
        dev = {
            "id": "device1",
            "status_topic": "stat/device/POWER",
            "cmd_topic": "cmnd/device/POWER",
        }

        is_valid = controller._validate_device_definition(dev)

        assert is_valid is False

    def test_validate_device_missing_status_topic(self, controller):
        """Test validating device without status_topic."""
        dev = {
            "id": "device1",
            "type": "switch",
            "cmd_topic": "cmnd/device/POWER",
        }

        is_valid = controller._validate_device_definition(dev)

        assert is_valid is False


class TestControllerNodeQueue:
    """Tests for node_queue method."""

    @pytest.fixture
    def controller(self):
        """Create a Controller instance for testing."""
        poly = Mock()
        poly.subscribe = Mock()
        poly.ready = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        for attr in [
            "START",
            "POLL",
            "LOGLEVEL",
            "CUSTOMPARAMS",
            "CUSTOMDATA",
            "STOP",
            "DISCOVER",
            "CUSTOMTYPEDDATA",
            "CUSTOMTYPEDPARAMS",
            "ADDNODEDONE",
        ]:
            setattr(poly, attr, attr)

        c = Controller(poly, "controller", "controller", "MQTT")
        return c

    def test_node_queue_adds_to_queue(self, controller):
        """Test that node_queue adds data to queue."""
        data = {"address": "device1"}

        controller.node_queue(data)

        assert len(controller.n_queue) == 1
        assert controller.n_queue[0] == "device1"  # Stores address not dict

    def test_node_queue_notifies_condition(self, controller):
        """Test that node_queue notifies waiting threads."""
        with patch.object(controller.queue_condition, "notify") as mock_notify:
            data = {"address": "device1"}

            controller.node_queue(data)

            mock_notify.assert_called_once()


class TestControllerHandleLevelChange:
    """Tests for handleLevelChange method."""

    @pytest.fixture
    def controller(self):
        """Create a Controller instance for testing."""
        poly = Mock()
        poly.subscribe = Mock()
        poly.ready = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        for attr in [
            "START",
            "POLL",
            "LOGLEVEL",
            "CUSTOMPARAMS",
            "CUSTOMDATA",
            "STOP",
            "DISCOVER",
            "CUSTOMTYPEDPARAMS",
            "CUSTOMTYPEDDATA",
            "ADDNODEDONE",
        ]:
            setattr(poly, attr, attr)

        c = Controller(poly, "controller", "controller", "MQTT")
        return c

    def test_handle_level_change_debug(self, controller):
        """Test handling log level change to DEBUG."""
        with patch("nodes.Controller.LOGGER") as _mock_logger:
            with patch("nodes.Controller.LOG_HANDLER") as mock_handler:
                controller.handleLevelChange({"level": 5})  # Level is a dict

                mock_handler.set_basic_config.assert_called()


class TestControllerPoll:
    """Tests for poll method."""

    @pytest.fixture
    def controller(self):
        """Create a Controller instance for testing."""
        poly = Mock()
        poly.subscribe = Mock()
        poly.ready = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        for attr in [
            "START",
            "POLL",
            "LOGLEVEL",
            "CUSTOMPARAMS",
            "CUSTOMDATA",
            "STOP",
            "DISCOVER",
            "CUSTOMTYPEDPARAMS",
            "CUSTOMTYPEDDATA",
            "ADDNODEDONE",
        ]:
            setattr(poly, attr, attr)

        c = Controller(poly, "controller", "controller", "MQTT")
        c.setDriver = Mock()
        return c

    def test_poll_increments_heartbeat(self, controller):
        """Test that poll increments heartbeat."""
        controller.ready_event.set()  # Set ready event
        controller.reportCmd = Mock()  # Mock reportCmd

        initial_hb = controller.hb

        controller.poll({"shortPoll": True})

        # Heartbeat toggles between True/False
        assert controller.hb != initial_hb

    def test_poll_sets_driver(self, controller):
        """Test that poll calls reportCmd."""
        controller.ready_event.set()  # Set ready event
        controller.reportCmd = Mock()

        controller.poll({"shortPoll": True})

        controller.reportCmd.assert_called()


class TestControllerQuery:
    """Tests for query method."""

    @pytest.fixture
    def controller(self):
        """Create a Controller instance for testing."""
        poly = Mock()
        poly.subscribe = Mock()
        poly.ready = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        for attr in [
            "START",
            "POLL",
            "LOGLEVEL",
            "CUSTOMPARAMS",
            "CUSTOMDATA",
            "STOP",
            "DISCOVER",
            "CUSTOMTYPEDPARAMS",
            "CUSTOMTYPEDDATA",
            "ADDNODEDONE",
        ]:
            setattr(poly, attr, attr)

        c = Controller(poly, "controller", "controller", "MQTT")
        c.reportDrivers = Mock()
        return c

    def test_query_reports_drivers(self, controller):
        """Test that query reports all drivers."""
        # Mock getNodes to return a dict
        mock_node1 = Mock()
        mock_node1.reportDrivers = Mock()
        mock_node2 = Mock()
        mock_node2.reportDrivers = Mock()

        controller.poly.getNodes = Mock(
            return_value={"node1": mock_node1, "node2": mock_node2}
        )

        controller.query()

        mock_node1.reportDrivers.assert_called_once()
        mock_node2.reportDrivers.assert_called_once()


class TestControllerDriversAndCommands:
    """Tests for node configuration."""

    def test_node_id(self):
        """Test that node ID is correct."""
        assert Controller.id == "mqctrl"

    def test_has_drivers(self):
        """Test that Controller has drivers defined."""
        assert hasattr(Controller, "drivers")
        assert isinstance(Controller.drivers, list)

    def test_has_commands(self):
        """Test that Controller has commands defined."""
        assert hasattr(Controller, "commands")
        assert isinstance(Controller.commands, dict)


class TestControllerIntegration:
    """Integration tests for Controller workflows."""

    @pytest.fixture
    def full_controller_setup(self):
        """Create a fully mocked Controller setup."""
        poly = Mock()
        poly.subscribe = Mock()
        poly.ready = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.addNode = Mock(return_value=True)
        poly.getNode = Mock(return_value=None)

        for attr in [
            "START",
            "POLL",
            "LOGLEVEL",
            "CUSTOMPARAMS",
            "CUSTOMDATA",
            "STOP",
            "DISCOVER",
            "CUSTOMTYPEDPARAMS",
            "CUSTOMTYPEDDATA",
            "ADDNODEDONE",
        ]:
            setattr(poly, attr, attr)

        c = Controller(poly, "controller", "controller", "MQTT")
        c.setDriver = Mock()
        c.reportDrivers = Mock()

        return c

    def test_initialization_workflow(self, full_controller_setup):
        """Test complete initialization workflow."""
        controller = full_controller_setup

        # Verify initial state
        assert controller.hb == 0
        assert controller.numNodes == 0
        assert controller.devlist == []
        assert controller.discovery_in is False

    def test_poll_workflow(self, full_controller_setup):
        """Test polling workflow."""
        controller = full_controller_setup
        controller.ready_event.set()
        controller.reportCmd = Mock()

        _initial_hb = controller.hb

        # Poll multiple times
        controller.poll({"shortPoll": True})
        controller.poll({"shortPoll": True})
        controller.poll({"shortPoll": True})

        # reportCmd should be called 3 times
        assert controller.reportCmd.call_count == 3

    def test_device_list_management(self, full_controller_setup):
        """Test device list management."""
        controller = full_controller_setup

        # Start with empty list
        assert len(controller.devlist) == 0

        # Simulate adding devices
        controller.devlist.append({"id": "device1", "type": "switch"})
        controller.devlist.append({"id": "device2", "type": "dimmer"})

        assert len(controller.devlist) == 2

    def test_status_topic_management(self, full_controller_setup):
        """Test status topic management."""
        controller = full_controller_setup

        # Start with empty topics
        assert len(controller.status_topics) == 0

        # Simulate adding topics
        controller.status_topics.append("stat/device1/POWER")
        controller.status_topics.append("stat/device2/POWER")

        assert len(controller.status_topics) == 2


class TestControllerDeviceConfig:
    """Tests for device configuration handling."""

    def test_device_config_switch(self):
        """Test switch device configuration."""
        config = DEVICE_CONFIG["switch"]
        assert "node_class" in config
        from nodes.MQSwitch import MQSwitch

        assert config["node_class"] == MQSwitch

    def test_device_config_dimmer(self):
        """Test dimmer device configuration."""
        config = DEVICE_CONFIG["dimmer"]
        assert "node_class" in config
        assert "extra_status_topics" in config
        from nodes.MQDimmer import MQDimmer

        assert config["node_class"] == MQDimmer

    def test_device_config_ratgdo(self):
        """Test ratgdo device configuration."""
        config = DEVICE_CONFIG["ratgdo"]
        assert "node_class" in config
        assert "status_topics" in config
        from nodes.MQratgdo import MQratgdo

        assert config["node_class"] == MQratgdo

    def test_device_config_all_have_node_class(self):
        """Test that all device configs have node_class."""
        for dev_type, config in DEVICE_CONFIG.items():
            assert "node_class" in config, f"{dev_type} missing node_class"


class TestControllerMqttPub:
    """Tests for mqtt_pub method."""

    @pytest.fixture
    def controller(self):
        """Create a Controller instance with MQTT client."""
        poly = Mock()
        poly.subscribe = Mock()
        poly.ready = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        for attr in [
            "START",
            "POLL",
            "LOGLEVEL",
            "CUSTOMPARAMS",
            "CUSTOMDATA",
            "STOP",
            "DISCOVER",
            "CUSTOMTYPEDPARAMS",
            "CUSTOMTYPEDDATA",
            "ADDNODEDONE",
        ]:
            setattr(poly, attr, attr)

        c = Controller(poly, "controller", "controller", "MQTT")
        c.mqttc = Mock()
        c.mqttc.publish = Mock()
        return c

    def test_mqtt_pub_publishes_message(self, controller):
        """Test that mqtt_pub publishes message."""
        controller.mqtt_pub("test/topic", "test_message")

        controller.mqttc.publish.assert_called_once_with(
            "test/topic", "test_message", retain=False
        )


class TestControllerStop:
    """Tests for stop method."""

    @pytest.fixture
    def controller(self):
        """Create a Controller instance."""
        poly = Mock()
        poly.subscribe = Mock()
        poly.ready = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        for attr in [
            "START",
            "POLL",
            "LOGLEVEL",
            "CUSTOMPARAMS",
            "CUSTOMDATA",
            "STOP",
            "DISCOVER",
            "CUSTOMTYPEDPARAMS",
            "CUSTOMTYPEDDATA",
            "ADDNODEDONE",
        ]:
            setattr(poly, attr, attr)

        c = Controller(poly, "controller", "controller", "MQTT")
        c.mqttc = Mock()
        c.mqttc.disconnect = Mock()
        c.mqttc.loop_stop = Mock()
        return c

    def test_stop_disconnects_mqtt(self, controller):
        """Test that stop disconnects MQTT client."""
        controller.stop()

        controller.mqttc.disconnect.assert_called_once()
        controller.mqttc.loop_stop.assert_called_once()


class TestControllerFormatDeviceAddress:
    """Tests for _format_device_address method."""

    @pytest.fixture
    def controller(self):
        """Create a Controller instance."""
        poly = Mock()
        poly.subscribe = Mock()
        poly.ready = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.getValidAddress = Mock(side_effect=lambda x: x.lower()[:14])
        for attr in [
            "START",
            "POLL",
            "LOGLEVEL",
            "CUSTOMPARAMS",
            "CUSTOMDATA",
            "STOP",
            "DISCOVER",
            "CUSTOMTYPEDPARAMS",
            "CUSTOMTYPEDDATA",
            "ADDNODEDONE",
        ]:
            setattr(poly, attr, attr)

        c = Controller(poly, "controller", "controller", "MQTT")
        return c

    def test_format_device_address_basic(self, controller):
        """Test formatting a basic device address."""
        dev = {"id": "test_device"}

        address = controller._format_device_address(dev)

        assert address == "testdevice"

    def test_format_device_address_with_underscores(self, controller):
        """Test formatting address with underscores."""
        dev = {"id": "test_device_123"}

        address = controller._format_device_address(dev)

        assert len(address) <= 14  # ISY address limit

    def test_format_device_address_with_hyphens(self, controller):
        """Test formatting address with hyphens."""
        dev = {"id": "test-device-456"}

        address = controller._format_device_address(dev)

        assert len(address) <= 14  # ISY address limit


class TestControllerCleanupNodes:
    """Tests for _cleanup_nodes method."""

    @pytest.fixture
    def controller(self):
        """Create a Controller instance."""
        poly = Mock()
        poly.subscribe = Mock()
        poly.ready = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.delNode = Mock()
        for attr in [
            "START",
            "POLL",
            "LOGLEVEL",
            "CUSTOMPARAMS",
            "CUSTOMDATA",
            "STOP",
            "DISCOVER",
            "CUSTOMTYPEDPARAMS",
            "CUSTOMTYPEDDATA",
            "ADDNODEDONE",
        ]:
            setattr(poly, attr, attr)

        c = Controller(poly, "controller", "controller", "MQTT")
        c._remove_status_topics = Mock()
        return c

    def test_cleanup_nodes_no_removals(self, controller):
        """Test cleanup when no nodes need removal."""
        nodes_new = ["node1", "node2"]
        nodes_old = ["node1", "node2"]

        result = controller._cleanup_nodes(nodes_new, nodes_old)

        assert result is True
        controller.poly.delNode.assert_not_called()

    def test_cleanup_nodes_removes_old_node(self, controller):
        """Test cleanup removes nodes not in new list."""
        nodes_new = ["node1", "node2"]
        nodes_old = ["node1", "node2", "node3"]

        result = controller._cleanup_nodes(nodes_new, nodes_old)

        assert result is True
        controller.poly.delNode.assert_called_once_with("node3")
        controller._remove_status_topics.assert_called_once_with("node3")

    def test_cleanup_nodes_removes_multiple(self, controller):
        """Test cleanup removes multiple old nodes."""
        nodes_new = ["node1"]
        nodes_old = ["node1", "node2", "node3"]

        result = controller._cleanup_nodes(nodes_new, nodes_old)

        assert result is True
        assert controller.poly.delNode.call_count == 2
        assert controller._remove_status_topics.call_count == 2


class TestControllerMqttSubscribe:
    """Tests for mqtt_subscribe method."""

    @pytest.fixture
    def controller(self):
        """Create a Controller instance with MQTT client."""
        poly = Mock()
        poly.subscribe = Mock()
        poly.ready = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.getNodes = Mock(return_value={"controller": Mock(), "node1": Mock()})
        poly.getNode = Mock()
        for attr in [
            "START",
            "POLL",
            "LOGLEVEL",
            "CUSTOMPARAMS",
            "CUSTOMDATA",
            "STOP",
            "DISCOVER",
            "CUSTOMTYPEDPARAMS",
            "CUSTOMTYPEDDATA",
            "ADDNODEDONE",
        ]:
            setattr(poly, attr, attr)

        c = Controller(poly, "controller", "controller", "MQTT")
        c.mqttc = Mock()
        c.status_topics = ["topic1", "topic2"]
        c.address = "controller"
        return c

    def test_mqtt_subscribe_success(self, controller):
        """Test successful MQTT subscription."""
        # Mock subscribe to return success (0, mid)
        controller.mqttc.subscribe = Mock(return_value=(0, 123))

        mock_node = Mock()
        mock_node.query = Mock()
        controller.poly.getNode.return_value = mock_node

        controller.mqtt_subscribe()

        # Should subscribe to all topics
        assert controller.mqttc.subscribe.call_count == 2
        # Should query child nodes
        mock_node.query.assert_called()

    def test_mqtt_subscribe_failure(self, controller):
        """Test MQTT subscription with failure."""
        # Mock subscribe to return failure (1, mid)
        controller.mqttc.subscribe = Mock(return_value=(1, 456))

        mock_node = Mock()
        mock_node.query = Mock()
        controller.poly.getNode.return_value = mock_node

        controller.mqtt_subscribe()

        # Should still attempt all subscriptions
        assert controller.mqttc.subscribe.call_count == 2


class TestControllerDelete:
    """Tests for delete method."""

    @pytest.fixture
    def controller(self):
        """Create a Controller instance."""
        poly = Mock()
        poly.subscribe = Mock()
        poly.ready = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        for attr in [
            "START",
            "POLL",
            "LOGLEVEL",
            "CUSTOMPARAMS",
            "CUSTOMDATA",
            "STOP",
            "DISCOVER",
            "CUSTOMTYPEDPARAMS",
            "CUSTOMTYPEDDATA",
            "ADDNODEDONE",
        ]:
            setattr(poly, attr, attr)

        c = Controller(poly, "controller", "controller", "MQTT")
        c.setDriver = Mock()
        return c

    def test_delete_sets_status_off(self, controller):
        """Test that delete sets status to 0."""
        controller.delete("DELETE")

        controller.setDriver.assert_called_once_with("ST", 0, report=True, force=True)


class TestControllerStopEnhanced:
    """Enhanced tests for stop method."""

    @pytest.fixture
    def controller(self):
        """Create a Controller instance."""
        poly = Mock()
        poly.subscribe = Mock()
        poly.ready = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        for attr in [
            "START",
            "POLL",
            "LOGLEVEL",
            "CUSTOMPARAMS",
            "CUSTOMDATA",
            "STOP",
            "DISCOVER",
            "CUSTOMTYPEDPARAMS",
            "CUSTOMTYPEDDATA",
            "ADDNODEDONE",
        ]:
            setattr(poly, attr, attr)

        c = Controller(poly, "controller", "controller", "MQTT")
        c.mqttc = Mock()
        c.mqttc.disconnect = Mock()
        c.mqttc.loop_stop = Mock()
        c.setDriver = Mock()
        c.Notices = Mock()
        c.Notices.clear = Mock()
        return c

    def test_stop_clears_notices(self, controller):
        """Test that stop clears notices."""
        controller.stop("STOP")

        controller.Notices.clear.assert_called_once()

    def test_stop_sets_status_off(self, controller):
        """Test that stop sets status to 0."""
        controller.stop("STOP")

        controller.setDriver.assert_called_once_with("ST", 0, report=True, force=True)


class TestControllerDiscoverCmd:
    """Tests for discover_cmd method."""

    @pytest.fixture
    def controller(self):
        """Create a Controller instance."""
        poly = Mock()
        poly.subscribe = Mock()
        poly.ready = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        for attr in [
            "START",
            "POLL",
            "LOGLEVEL",
            "CUSTOMPARAMS",
            "CUSTOMDATA",
            "STOP",
            "DISCOVER",
            "CUSTOMTYPEDPARAMS",
            "CUSTOMTYPEDDATA",
            "ADDNODEDONE",
        ]:
            setattr(poly, attr, attr)

        c = Controller(poly, "controller", "controller", "MQTT")
        c.checkParams = Mock(return_value=True)
        c._discover = Mock(return_value=True)
        return c

    def test_discover_cmd_success(self, controller):
        """Test successful discovery."""
        result = controller.discover_cmd("DISCOVER")

        assert result is True
        assert controller.discovery_in is False
        controller.checkParams.assert_called_once()
        controller._discover.assert_called_once()

    def test_discover_cmd_already_running(self, controller):
        """Test discovery when already running."""
        controller.discovery_in = True

        result = controller.discover_cmd("DISCOVER")

        assert result is False
        controller.checkParams.assert_not_called()

    def test_discover_cmd_check_params_fails(self, controller):
        """Test discovery when checkParams fails."""
        controller.checkParams.return_value = False

        result = controller.discover_cmd("DISCOVER")

        assert result is False
        assert controller.discovery_in is False

    def test_discover_cmd_discover_fails(self, controller):
        """Test discovery when _discover fails."""
        controller._discover.return_value = False

        result = controller.discover_cmd("DISCOVER")

        assert result is False
        assert controller.discovery_in is False


class TestControllerCheckParams:
    """Tests for checkParams method."""

    @pytest.fixture
    def controller(self):
        """Create a Controller instance."""
        poly = Mock()
        poly.subscribe = Mock()
        poly.ready = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        for attr in [
            "START",
            "POLL",
            "LOGLEVEL",
            "CUSTOMPARAMS",
            "CUSTOMDATA",
            "STOP",
            "DISCOVER",
            "CUSTOMTYPEDPARAMS",
            "CUSTOMTYPEDDATA",
            "ADDNODEDONE",
        ]:
            setattr(poly, attr, attr)

        c = Controller(poly, "controller", "controller", "MQTT")
        c._load_devfile_config = Mock(return_value=True)
        c._load_devlist_config = Mock(return_value=True)
        c._load_mqtt_parameters = Mock(return_value=True)
        return c

    def test_check_params_with_devfile(self, controller):
        """Test checkParams with devfile."""
        controller.Parameters = Mock()
        controller.Parameters.get = Mock(return_value="file.yaml")

        result = controller.checkParams()

        assert result is True
        controller._load_devfile_config.assert_called_once()
        controller._load_mqtt_parameters.assert_called_once()

    def test_check_params_with_devlist(self, controller):
        """Test checkParams with devlist."""

        def mock_get(x):
            if x == "devfile":
                return None
            elif x == "devlist":
                return "[]"
            return None

        controller.Parameters = Mock()
        controller.Parameters.get = Mock(side_effect=mock_get)

        result = controller.checkParams()

        assert result is True
        controller._load_devlist_config.assert_called_once()
        controller._load_mqtt_parameters.assert_called_once()

    def test_check_params_no_config(self, controller):
        """Test checkParams without devfile or devlist."""
        controller.Parameters.get = Mock(return_value=None)

        result = controller.checkParams()

        assert result is False
        controller._load_devfile_config.assert_not_called()
        controller._load_devlist_config.assert_not_called()

    def test_check_params_devfile_load_fails(self, controller):
        """Test checkParams when devfile load fails."""
        controller.Parameters.get = Mock(
            side_effect=lambda x: "file.yaml" if x == "devfile" else None
        )
        controller._load_devfile_config.return_value = False

        result = controller.checkParams()

        assert result is False

    def test_check_params_mqtt_load_fails(self, controller):
        """Test checkParams when MQTT parameter load fails."""
        controller.Parameters.get = Mock(
            side_effect=lambda x: "file.yaml" if x == "devfile" else None
        )
        controller._load_mqtt_parameters.return_value = False

        result = controller.checkParams()

        assert result is False


class TestControllerHeartbeat:
    """Tests for heartbeat method."""

    @pytest.fixture
    def controller(self):
        """Create a Controller instance."""
        poly = Mock()
        poly.subscribe = Mock()
        poly.ready = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        for attr in [
            "START",
            "POLL",
            "LOGLEVEL",
            "CUSTOMPARAMS",
            "CUSTOMDATA",
            "STOP",
            "DISCOVER",
            "CUSTOMTYPEDPARAMS",
            "CUSTOMTYPEDDATA",
            "ADDNODEDONE",
        ]:
            setattr(poly, attr, attr)

        c = Controller(poly, "controller", "controller", "MQTT")
        c.reportCmd = Mock()
        return c

    def test_heartbeat_sends_don_when_hb_false(self, controller):
        """Test heartbeat sends DON when hb is False."""
        controller.hb = False

        controller.heartbeat()

        controller.reportCmd.assert_called_once_with("DON", 2)
        assert controller.hb is True

    def test_heartbeat_sends_dof_when_hb_true(self, controller):
        """Test heartbeat sends DOF when hb is True."""
        controller.hb = True

        controller.heartbeat()

        controller.reportCmd.assert_called_once_with("DOF", 2)
        assert controller.hb is False

    def test_heartbeat_alternates(self, controller):
        """Test heartbeat alternates between DON and DOF."""
        controller.hb = False

        # First call
        controller.heartbeat()
        controller.reportCmd.assert_called_with("DON", 2)
        assert controller.hb is True

        # Second call
        controller.heartbeat()
        controller.reportCmd.assert_called_with("DOF", 2)
        assert controller.hb is False
