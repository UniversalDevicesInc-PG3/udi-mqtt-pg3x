"""
Comprehensive test suite for MQAnalog node.

Tests cover:
- Initialization (single and multi-sensor)
- JSON payload parsing
- Tasmota StatusSNS wrapper handling
- Single sensor mode (default)
- Multi-sensor mode (with sensor_id)
- Query command with MQTT pub
- Edge cases and error handling
"""

import json
import pytest
from unittest.mock import Mock
from nodes.MQAnalog import MQAnalog, DEFAULT_SENSOR_ID


class TestMQAnalogInitialization:
    """Tests for MQAnalog initialization."""

    @pytest.fixture
    def mock_polyglot(self):
        """Create a mock polyglot interface."""
        poly = Mock()
        poly.getNode = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        return poly

    @pytest.fixture
    def device_config(self):
        """Create a sample device configuration."""
        return {"cmd_topic": "home/analog/1/cmd"}

    def test_initialization_single_sensor(self, mock_polyglot, device_config):
        """Test initialization for single sensor (default)."""
        controller = Mock()
        mock_polyglot.getNode.return_value = controller

        analog = MQAnalog(
            mock_polyglot, "controller", "analog_1", "Analog Sensor", device_config
        )

        assert analog.id == "mqanal"
        assert analog.address == "analog_1"
        assert analog.name == "Analog Sensor"
        assert analog.cmd_topic == "home/analog/1/cmd"
        assert analog.lpfx == "analog_1:Analog Sensor"
        assert analog.sensor_id == DEFAULT_SENSOR_ID
        assert analog.controller == controller

    def test_initialization_multi_sensor(self, mock_polyglot):
        """Test initialization for multi-sensor with specific sensor_id."""
        mock_polyglot.getNode.return_value = Mock()
        device = {"cmd_topic": "home/analog/cmd", "sensor_id": "A1"}

        analog = MQAnalog(mock_polyglot, "controller", "analog_2", "Test", device)

        assert analog.sensor_id == "A1"

    def test_initialization_custom_sensor_id(self, mock_polyglot):
        """Test initialization with custom sensor ID."""
        mock_polyglot.getNode.return_value = Mock()
        device = {"cmd_topic": "test/cmd", "sensor_id": "Temperature"}

        analog = MQAnalog(mock_polyglot, "controller", "a1", "Test", device)

        assert analog.sensor_id == "Temperature"


class TestMQAnalogUpdateInfo:
    """Tests for updateInfo method (JSON message handling)."""

    @pytest.fixture
    def single_sensor(self):
        """Create a MQAnalog instance in single-sensor mode."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        poly.getNode = Mock(return_value=Mock())

        device = {"cmd_topic": "test/cmd"}
        node = MQAnalog(poly, "controller", "analog1", "Test", device)
        node.setDriver = Mock()

        return node

    @pytest.fixture
    def multi_sensor(self):
        """Create a MQAnalog instance in multi-sensor mode."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        poly.getNode = Mock(return_value=Mock())

        device = {"cmd_topic": "test/cmd", "sensor_id": "A0"}
        node = MQAnalog(poly, "controller", "analog1", "Test", device)
        node.setDriver = Mock()

        return node

    def test_update_info_single_sensor(self, single_sensor):
        """Test handling single sensor analog reading."""
        payload = json.dumps({"ANALOG": {"A0": 512}})

        single_sensor.updateInfo(payload, "test/state")

        # Should set ST to 1 (online) and GPV to the value
        calls = single_sensor.setDriver.call_args_list
        assert len(calls) == 2
        assert calls[0] == (("ST", 1),)
        assert calls[1] == (("GPV", 512),)

    def test_update_info_multi_sensor_specific(self, multi_sensor):
        """Test handling multi-sensor with specific sensor_id."""
        payload = json.dumps({"ANALOG": {"A0": 256, "A1": 789, "A2": 123}})

        multi_sensor.updateInfo(payload, "test/state")

        # Should extract only A0 value
        calls = multi_sensor.setDriver.call_args_list
        assert len(calls) == 2
        assert calls[0] == (("ST", 1),)
        assert calls[1] == (("GPV", 256),)

    def test_update_info_tasmota_wrapper(self, single_sensor):
        """Test handling Tasmota StatusSNS wrapper."""
        payload = json.dumps({"StatusSNS": {"ANALOG": {"A0": 1024}}})

        single_sensor.updateInfo(payload, "test/state")

        # Should unwrap StatusSNS and process
        calls = single_sensor.setDriver.call_args_list
        assert len(calls) == 2
        assert calls[0] == (("ST", 1),)
        assert calls[1] == (("GPV", 1024),)

    def test_update_info_no_analog_data(self, single_sensor):
        """Test handling payload without ANALOG field."""
        payload = json.dumps({"Temperature": 72, "Humidity": 50})

        single_sensor.updateInfo(payload, "test/state")

        # Should set ST and GPV to 0
        calls = single_sensor.setDriver.call_args_list
        assert len(calls) == 2
        assert calls[0] == (("ST", 0),)
        assert calls[1] == (("GPV", 0),)

    def test_update_info_analog_not_dict(self, single_sensor):
        """Test handling ANALOG field that is not a dict."""
        payload = json.dumps({"ANALOG": "not_a_dict"})

        single_sensor.updateInfo(payload, "test/state")

        # Should handle gracefully
        calls = single_sensor.setDriver.call_args_list
        assert len(calls) == 2
        assert calls[0] == (("ST", 0),)
        assert calls[1] == (("GPV", 0),)

    def test_update_info_empty_analog_dict(self, single_sensor):
        """Test handling empty ANALOG dictionary."""
        payload = json.dumps({"ANALOG": {}})

        single_sensor.updateInfo(payload, "test/state")

        # Should set ST to 1 but not update GPV (StopIteration)
        calls = single_sensor.setDriver.call_args_list
        assert calls[0] == (("ST", 1),)

    def test_update_info_multi_sensor_missing_id(self, multi_sensor):
        """Test multi-sensor mode with missing sensor_id."""
        payload = json.dumps({"ANALOG": {"A1": 500, "A2": 600}})

        multi_sensor.updateInfo(payload, "test/state")

        # Should set ST to 1 but not find A0
        calls = multi_sensor.setDriver.call_args_list
        assert calls[0] == (("ST", 1),)
        # GPV should not be updated due to KeyError

    def test_update_info_invalid_json(self, single_sensor):
        """Test handling invalid JSON payload."""
        payload = "not valid json {"

        single_sensor.updateInfo(payload, "test/state")

        # Should not call setDriver due to JSON error
        single_sensor.setDriver.assert_not_called()

    def test_update_info_multiple_sensors_single_mode(self, single_sensor):
        """Test single-sensor mode picks first sensor from multiple."""
        payload = json.dumps({"ANALOG": {"Sensor1": 100, "Sensor2": 200}})

        single_sensor.updateInfo(payload, "test/state")

        # Should use first sensor (dict iteration order)
        calls = single_sensor.setDriver.call_args_list
        assert calls[0] == (("ST", 1),)
        assert calls[1][0][0] == "GPV"
        # Value should be from first sensor (order may vary in dicts)
        assert calls[1][0][1] in [100, 200]

    def test_update_info_zero_value(self, single_sensor):
        """Test handling zero analog value."""
        payload = json.dumps({"ANALOG": {"A0": 0}})

        single_sensor.updateInfo(payload, "test/state")

        calls = single_sensor.setDriver.call_args_list
        assert calls[0] == (("ST", 1),)
        assert calls[1] == (("GPV", 0),)

    def test_update_info_max_value(self, single_sensor):
        """Test handling maximum analog value."""
        payload = json.dumps({"ANALOG": {"A0": 4095}})

        single_sensor.updateInfo(payload, "test/state")

        calls = single_sensor.setDriver.call_args_list
        assert calls[1] == (("GPV", 4095),)

    def test_update_info_tasmota_with_multi_sensor(self, multi_sensor):
        """Test Tasmota wrapper with multi-sensor mode."""
        payload = json.dumps({
            "StatusSNS": {
                "ANALOG": {"A0": 333, "A1": 444}
            }
        })

        multi_sensor.updateInfo(payload, "test/state")

        # Should unwrap and extract A0
        calls = multi_sensor.setDriver.call_args_list
        assert calls[1] == (("GPV", 333),)


class TestMQAnalogQuery:
    """Tests for query command."""

    @pytest.fixture
    def analog_with_controller(self):
        """Create a MQAnalog with mocked controller."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "home/device/cmnd/Status"}
        node = MQAnalog(poly, "controller", "analog1", "Test", device)
        node.reportDrivers = Mock()

        return node

    def test_query_command_basic(self, analog_with_controller):
        """Test QUERY command publishes status request."""
        command = {"cmd": "QUERY"}

        analog_with_controller.query(command)

        # Should publish to Status topic with "10" command
        analog_with_controller.controller.mqtt_pub.assert_called_once_with(
            "home/device/cmnd/Status", "10"
        )
        analog_with_controller.reportDrivers.assert_called_once()

    def test_query_command_topic_parsing(self, analog_with_controller):
        """Test query correctly parses and constructs status topic."""
        analog_with_controller.cmd_topic = "tasmota/device/cmd"

        analog_with_controller.query(None)

        # Should replace last segment with 'Status'
        analog_with_controller.controller.mqtt_pub.assert_called_once_with(
            "tasmota/device/Status", "10"
        )

    def test_query_command_simple_topic(self):
        """Test query with simple single-segment topic."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "cmd"}
        node = MQAnalog(poly, "controller", "a1", "Test", device)
        node.reportDrivers = Mock()

        node.query(None)

        # Should handle edge case of simple topic
        controller.mqtt_pub.assert_called_once()
        args = controller.mqtt_pub.call_args[0]
        assert args[1] == "10"


class TestMQAnalogDriversAndCommands:
    """Tests for node configuration."""

    def test_node_id(self):
        """Test node ID is correct."""
        assert MQAnalog.id == "mqanal"

    def test_drivers_configuration(self):
        """Test drivers are properly configured."""
        assert len(MQAnalog.drivers) == 2

        # Check ST driver
        st_driver = MQAnalog.drivers[0]
        assert st_driver["driver"] == "ST"
        assert st_driver["value"] == 0
        assert st_driver["uom"] == 2
        assert st_driver["name"] == "Analog ST"

        # Check GPV driver
        gpv_driver = MQAnalog.drivers[1]
        assert gpv_driver["driver"] == "GPV"
        assert gpv_driver["value"] == 0
        assert gpv_driver["uom"] == 56
        assert gpv_driver["name"] == "Analog"

    def test_commands_configuration(self):
        """Test commands are properly configured."""
        assert "QUERY" in MQAnalog.commands
        assert MQAnalog.commands["QUERY"] == MQAnalog.query

    def test_default_sensor_id_constant(self):
        """Test DEFAULT_SENSOR_ID constant."""
        assert DEFAULT_SENSOR_ID == "SINGLE_SENSOR"


class TestMQAnalogIntegration:
    """Integration tests for complete workflows."""

    @pytest.fixture
    def full_setup(self):
        """Create a fully mocked setup."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "home/adc/cmnd"}
        node = MQAnalog(poly, "controller", "adc1", "ADC Sensor", device)
        node.setDriver = Mock()
        node.reportDrivers = Mock()

        return node

    def test_single_sensor_workflow(self, full_setup):
        """Test single sensor reading workflow."""
        sensor = full_setup

        # Initial reading
        payload = json.dumps({"ANALOG": {"A0": 512}})
        sensor.updateInfo(payload, "home/adc/state")

        assert sensor.setDriver.call_args_list[0] == (("ST", 1),)
        assert sensor.setDriver.call_args_list[1] == (("GPV", 512),)

        sensor.setDriver.reset_mock()

        # Updated reading
        payload = json.dumps({"ANALOG": {"A0": 768}})
        sensor.updateInfo(payload, "home/adc/state")

        assert sensor.setDriver.call_args_list[1] == (("GPV", 768),)

    def test_tasmota_device_workflow(self, full_setup):
        """Test workflow with Tasmota device."""
        sensor = full_setup

        # Tasmota sends StatusSNS wrapper
        payload = json.dumps({
            "StatusSNS": {
                "Time": "2025-01-01T12:00:00",
                "ANALOG": {"A0": 1024}
            }
        })

        sensor.updateInfo(payload, "home/adc/tele/SENSOR")

        # Should unwrap and process
        assert sensor.setDriver.call_args_list[1] == (("GPV", 1024),)

    def test_query_and_response_workflow(self, full_setup):
        """Test query command followed by response."""
        sensor = full_setup

        # Send query
        sensor.query({"cmd": "QUERY"})

        # Verify MQTT publish was called
        sensor.controller.mqtt_pub.assert_called_once()

        # Simulate response
        sensor.setDriver.reset_mock()
        payload = json.dumps({"StatusSNS": {"ANALOG": {"A0": 555}}})
        sensor.updateInfo(payload, "home/adc/state")

        assert sensor.setDriver.call_args_list[1] == (("GPV", 555),)

    def test_error_recovery_workflow(self, full_setup):
        """Test error and recovery workflow."""
        sensor = full_setup

        # Valid reading
        payload = json.dumps({"ANALOG": {"A0": 100}})
        sensor.updateInfo(payload, "home/adc/state")
        assert sensor.setDriver.call_args_list[0] == (("ST", 1),)

        sensor.setDriver.reset_mock()

        # Error - no ANALOG data
        payload = json.dumps({"Temperature": 25})
        sensor.updateInfo(payload, "home/adc/state")
        assert sensor.setDriver.call_args_list[0] == (("ST", 0),)

        sensor.setDriver.reset_mock()

        # Recovery
        payload = json.dumps({"ANALOG": {"A0": 200}})
        sensor.updateInfo(payload, "home/adc/state")
        assert sensor.setDriver.call_args_list[0] == (("ST", 1),)
        assert sensor.setDriver.call_args_list[1] == (("GPV", 200),)

    def test_multi_sensor_selection_workflow(self):
        """Test multi-sensor device with specific sensor selection."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        poly.getNode.return_value = controller

        # Configure for A1 sensor only
        device = {"cmd_topic": "test/cmd", "sensor_id": "A1"}
        sensor = MQAnalog(poly, "controller", "s1", "A1 Sensor", device)
        sensor.setDriver = Mock()

        # Payload with multiple sensors
        payload = json.dumps({
            "ANALOG": {
                "A0": 100,
                "A1": 200,
                "A2": 300
            }
        })

        sensor.updateInfo(payload, "test/state")

        # Should only extract A1
        assert sensor.setDriver.call_args_list[1] == (("GPV", 200),)
