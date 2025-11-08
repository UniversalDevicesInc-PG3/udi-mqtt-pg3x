"""
Comprehensive test suite for MQdht node.

Tests cover:
- Initialization with sensor_id configuration
- JSON payload parsing for DHT temp/humidity sensors
- Temperature, humidity, and dew point handling
- Tasmota StatusSNS wrapper support
- Query command with MQTT publishing
- Edge cases and error handling
"""

import json
import pytest
from unittest.mock import Mock
from nodes.MQdht import MQdht, DEFAULT_SENSOR_ID


class TestMQdhtInitialization:
    """Tests for MQdht initialization."""

    @pytest.fixture
    def mock_polyglot(self):
        """Create a mock polyglot interface."""
        poly = Mock()
        poly.getNode = Mock(return_value=Mock())
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        return poly

    @pytest.fixture
    def device_config(self):
        """Create a sample device configuration."""
        return {"cmd_topic": "tele/dht/cmnd/Status"}

    def test_initialization_default_sensor_id(self, mock_polyglot, device_config):
        """Test initialization with default sensor ID."""
        dht = MQdht(mock_polyglot, "controller", "dht_1", "DHT Sensor", device_config)

        assert dht.id == "mqdht"
        assert dht.address == "dht_1"
        assert dht.name == "DHT Sensor"
        assert dht.lpfx == "dht_1:DHT Sensor"
        assert dht.cmd_topic == "tele/dht/cmnd/Status"
        assert dht.sensor_id == DEFAULT_SENSOR_ID
        assert device_config["sensor_id"] == DEFAULT_SENSOR_ID

    def test_initialization_custom_sensor_id(self, mock_polyglot):
        """Test initialization with custom sensor ID."""
        device = {
            "cmd_topic": "tele/am2301/cmnd/Status",
            "sensor_id": "AM2301",
        }
        dht = MQdht(mock_polyglot, "controller", "am2301", "AM2301", device)

        assert dht.sensor_id == "AM2301"
        assert device["sensor_id"] == "AM2301"

    def test_initialization_adds_default_sensor_id(self, mock_polyglot):
        """Test that default sensor_id is added to device if not present."""
        device = {"cmd_topic": "test/cmd"}
        dht = MQdht(mock_polyglot, "controller", "dht", "DHT", device)

        assert "sensor_id" in device
        assert device["sensor_id"] == DEFAULT_SENSOR_ID


class TestMQdhtUpdateInfo:
    """Tests for updateInfo method (sensor data handling)."""

    @pytest.fixture
    def dht_node(self):
        """Create a MQdht instance for testing."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        poly.getNode = Mock(return_value=Mock())

        device = {
            "cmd_topic": "test/cmd",
            "sensor_id": DEFAULT_SENSOR_ID,
        }
        node = MQdht(poly, "controller", "dht", "Test", device)
        node.setDriver = Mock()

        return node

    def test_update_info_complete_data(self, dht_node):
        """Test handling complete sensor data."""
        payload = json.dumps({
            DEFAULT_SENSOR_ID: {
                "Temperature": 72.5,
                "Humidity": 55.0,
                "DewPoint": 54.3,
            }
        })

        dht_node.updateInfo(payload, "test/dht/tele/SENSOR")

        calls = dht_node.setDriver.call_args_list
        assert len(calls) == 4
        assert calls[0] == (("ST", 1),)
        assert calls[1] == (("CLITEMP", 72.5),)
        assert calls[2] == (("CLIHUM", 55.0),)
        assert calls[3] == (("DEWPT", 54.3),)

    def test_update_info_partial_data(self, dht_node):
        """Test handling partial sensor data (missing some fields)."""
        payload = json.dumps({
            DEFAULT_SENSOR_ID: {
                "Temperature": 68.0,
                "Humidity": 60.0,
            }
        })

        dht_node.updateInfo(payload, "test/dht/tele/SENSOR")

        calls = dht_node.setDriver.call_args_list
        assert calls[0] == (("ST", 1),)
        assert calls[1] == (("CLITEMP", 68.0),)
        assert calls[2] == (("CLIHUM", 60.0),)
        assert calls[3] == (("DEWPT", None),)

    def test_update_info_tasmota_statussns_wrapper(self, dht_node):
        """Test handling Tasmota StatusSNS wrapper."""
        payload = json.dumps({
            "StatusSNS": {
                DEFAULT_SENSOR_ID: {
                    "Temperature": 75.0,
                    "Humidity": 50.0,
                    "DewPoint": 55.0,
                }
            }
        })

        dht_node.updateInfo(payload, "test/dht/stat/STATUS10")

        calls = dht_node.setDriver.call_args_list
        assert calls[0] == (("ST", 1),)
        assert calls[1] == (("CLITEMP", 75.0),)
        assert calls[2] == (("CLIHUM", 50.0),)
        assert calls[3] == (("DEWPT", 55.0),)

    def test_update_info_custom_sensor_id(self, dht_node):
        """Test handling data with custom sensor ID."""
        dht_node.sensor_id = "AM2301"

        payload = json.dumps({
            "AM2301": {
                "Temperature": 70.0,
                "Humidity": 45.0,
                "DewPoint": 50.0,
            }
        })

        dht_node.updateInfo(payload, "test/am2301/tele/SENSOR")

        calls = dht_node.setDriver.call_args_list
        assert calls[0] == (("ST", 1),)
        assert calls[1] == (("CLITEMP", 70.0),)

    def test_update_info_no_sensor_key(self, dht_node):
        """Test handling payload without sensor key."""
        payload = json.dumps({"Time": "2025-01-01T12:00:00"})

        dht_node.updateInfo(payload, "test/dht/tele/SENSOR")

        calls = dht_node.setDriver.call_args_list
        assert len(calls) == 1
        assert calls[0] == (("ST", 0),)

    def test_update_info_sensor_not_dict(self, dht_node):
        """Test handling sensor field that is not a dict."""
        payload = json.dumps({DEFAULT_SENSOR_ID: "not_a_dict"})

        dht_node.updateInfo(payload, "test/dht/tele/SENSOR")

        calls = dht_node.setDriver.call_args_list
        assert calls[0] == (("ST", 0),)

    def test_update_info_sensor_is_none(self, dht_node):
        """Test handling sensor field that is None."""
        payload = json.dumps({DEFAULT_SENSOR_ID: None})

        dht_node.updateInfo(payload, "test/dht/tele/SENSOR")

        calls = dht_node.setDriver.call_args_list
        assert calls[0] == (("ST", 0),)

    def test_update_info_invalid_json(self, dht_node):
        """Test handling invalid JSON payload."""
        payload = "not valid json {"

        dht_node.updateInfo(payload, "test/dht/tele/SENSOR")

        dht_node.setDriver.assert_not_called()

    def test_update_info_empty_json(self, dht_node):
        """Test handling empty JSON object."""
        payload = json.dumps({})

        dht_node.updateInfo(payload, "test/dht/tele/SENSOR")

        calls = dht_node.setDriver.call_args_list
        assert calls[0] == (("ST", 0),)

    def test_update_info_empty_sensor_dict(self, dht_node):
        """Test handling empty sensor dictionary."""
        payload = json.dumps({DEFAULT_SENSOR_ID: {}})

        dht_node.updateInfo(payload, "test/dht/tele/SENSOR")

        calls = dht_node.setDriver.call_args_list
        assert calls[0] == (("ST", 1),)
        assert calls[1] == (("CLITEMP", None),)
        assert calls[2] == (("CLIHUM", None),)
        assert calls[3] == (("DEWPT", None),)

    def test_update_info_zero_values(self, dht_node):
        """Test handling zero temperature and humidity."""
        payload = json.dumps({
            DEFAULT_SENSOR_ID: {
                "Temperature": 0,
                "Humidity": 0,
                "DewPoint": -10,
            }
        })

        dht_node.updateInfo(payload, "test/dht/tele/SENSOR")

        calls = dht_node.setDriver.call_args_list
        assert calls[1] == (("CLITEMP", 0),)
        assert calls[2] == (("CLIHUM", 0),)
        assert calls[3] == (("DEWPT", -10),)

    def test_update_info_negative_temperature(self, dht_node):
        """Test handling negative temperatures (freezing conditions)."""
        payload = json.dumps({
            DEFAULT_SENSOR_ID: {
                "Temperature": -5.0,
                "Humidity": 80.0,
                "DewPoint": -8.5,
            }
        })

        dht_node.updateInfo(payload, "test/dht/tele/SENSOR")

        calls = dht_node.setDriver.call_args_list
        assert calls[1] == (("CLITEMP", -5.0),)
        assert calls[3] == (("DEWPT", -8.5),)

    def test_update_info_high_temperature(self, dht_node):
        """Test handling high temperatures."""
        payload = json.dumps({
            DEFAULT_SENSOR_ID: {
                "Temperature": 95.0,
                "Humidity": 90.0,
                "DewPoint": 92.0,
            }
        })

        dht_node.updateInfo(payload, "test/dht/tele/SENSOR")

        calls = dht_node.setDriver.call_args_list
        assert calls[1] == (("CLITEMP", 95.0),)
        assert calls[2] == (("CLIHUM", 90.0),)

    def test_update_info_extra_fields_ignored(self, dht_node):
        """Test that extra fields in payload are ignored."""
        payload = json.dumps({
            DEFAULT_SENSOR_ID: {
                "Temperature": 70.0,
                "Humidity": 50.0,
                "DewPoint": 52.0,
                "ExtraField": "ignored",
                "Other": 999,
            },
            "Time": "2025-01-01T12:00:00",
        })

        dht_node.updateInfo(payload, "test/dht/tele/SENSOR")

        calls = dht_node.setDriver.call_args_list
        assert len(calls) == 4
        assert calls[1] == (("CLITEMP", 70.0),)

    def test_update_info_tasmota_statussns_with_other_data(self, dht_node):
        """Test Tasmota StatusSNS wrapper with additional data."""
        payload = json.dumps({
            "StatusSNS": {
                "Time": "2025-01-01T12:00:00",
                DEFAULT_SENSOR_ID: {
                    "Temperature": 73.0,
                    "Humidity": 48.0,
                    "DewPoint": 51.0,
                },
            }
        })

        dht_node.updateInfo(payload, "test/dht/stat/STATUS10")

        calls = dht_node.setDriver.call_args_list
        assert calls[0] == (("ST", 1),)
        assert calls[1] == (("CLITEMP", 73.0),)


class TestMQdhtQuery:
    """Tests for query command."""

    @pytest.fixture
    def dht_with_controller(self):
        """Create a MQdht with mocked controller."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()

        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode = Mock(return_value=controller)

        device = {"cmd_topic": "tele/dht/cmnd/Status"}
        node = MQdht(poly, "controller", "dht", "Test", device)
        node.reportDrivers = Mock()

        return node, controller

    def test_query_command(self, dht_with_controller):
        """Test QUERY command publishes status request."""
        dht, controller = dht_with_controller
        command = {"cmd": "QUERY"}

        dht.query(command)

        controller.mqtt_pub.assert_called_once_with("tele/dht/cmnd/Status", "10")
        dht.reportDrivers.assert_called_once()

    def test_query_command_none(self, dht_with_controller):
        """Test QUERY command with None parameter."""
        dht, controller = dht_with_controller

        dht.query(None)

        controller.mqtt_pub.assert_called_once_with("tele/dht/cmnd/Status", "10")
        dht.reportDrivers.assert_called_once()

    def test_query_command_extracts_topic(self, dht_with_controller):
        """Test QUERY command correctly extracts topic from cmd_topic."""
        dht, controller = dht_with_controller
        dht.cmd_topic = "tele/bedroom/dht/cmnd/Power"

        dht.query({"cmd": "QUERY"})

        controller.mqtt_pub.assert_called_once_with("tele/bedroom/dht/cmnd/Status", "10")

    def test_query_command_simple_topic(self, dht_with_controller):
        """Test QUERY command with simple topic path."""
        dht, controller = dht_with_controller
        dht.cmd_topic = "dht/Power"

        dht.query({"cmd": "QUERY"})

        controller.mqtt_pub.assert_called_once_with("dht/Status", "10")


class TestMQdhtDriversAndCommands:
    """Tests for node configuration."""

    def test_node_id(self):
        """Test node ID is correct."""
        assert MQdht.id == "mqdht"

    def test_drivers_configuration(self):
        """Test drivers are properly configured."""
        assert len(MQdht.drivers) == 4

        driver_dict = {d["driver"]: d for d in MQdht.drivers}

        assert driver_dict["ST"]["uom"] == 2  # boolean
        assert driver_dict["ST"]["name"] == "AM2301 ST"

        assert driver_dict["CLITEMP"]["uom"] == 17  # Fahrenheit
        assert driver_dict["CLITEMP"]["name"] == "Temperature"

        assert driver_dict["CLIHUM"]["uom"] == 22  # relative humidity
        assert driver_dict["CLIHUM"]["name"] == "Humidity"

        assert driver_dict["DEWPT"]["uom"] == 17  # Fahrenheit
        assert driver_dict["DEWPT"]["name"] == "Dew Point"

    def test_commands_configuration(self):
        """Test commands are properly configured."""
        assert "QUERY" in MQdht.commands
        assert MQdht.commands["QUERY"] == MQdht.query

    def test_default_sensor_id_constant(self):
        """Test DEFAULT_SENSOR_ID constant."""
        assert DEFAULT_SENSOR_ID == "SINGLE_SENSOR"


class TestMQdhtIntegration:
    """Integration tests for complete workflows."""

    @pytest.fixture
    def full_setup(self):
        """Create a fully mocked setup."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()

        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode = Mock(return_value=controller)

        device = {
            "cmd_topic": "tele/bedroom/dht/cmnd/Status",
            "sensor_id": "AM2301",
        }
        node = MQdht(poly, "controller", "bedroom_dht", "Bedroom Sensor", device)
        node.setDriver = Mock()
        node.reportDrivers = Mock()

        return node, controller

    def test_temperature_monitoring_workflow(self, full_setup):
        """Test continuous temperature monitoring."""
        dht, _ = full_setup

        # Morning - cool temperature
        payload = json.dumps({
            "AM2301": {
                "Temperature": 68.0,
                "Humidity": 55.0,
                "DewPoint": 50.0,
            }
        })
        dht.updateInfo(payload, "tele/bedroom/dht/tele/SENSOR")

        assert dht.setDriver.call_args_list[0] == (("ST", 1),)
        assert dht.setDriver.call_args_list[1] == (("CLITEMP", 68.0),)
        assert dht.setDriver.call_args_list[2] == (("CLIHUM", 55.0),)

        dht.setDriver.reset_mock()

        # Afternoon - warmer
        payload = json.dumps({
            "AM2301": {
                "Temperature": 78.0,
                "Humidity": 45.0,
                "DewPoint": 55.0,
            }
        })
        dht.updateInfo(payload, "tele/bedroom/dht/tele/SENSOR")

        assert dht.setDriver.call_args_list[1] == (("CLITEMP", 78.0),)

    def test_query_and_response_workflow(self, full_setup):
        """Test query command and subsequent response."""
        dht, controller = full_setup

        # Send query
        dht.query({"cmd": "QUERY"})

        controller.mqtt_pub.assert_called_once_with("tele/bedroom/dht/cmnd/Status", "10")
        dht.reportDrivers.assert_called_once()

        # Receive Tasmota response
        payload = json.dumps({
            "StatusSNS": {
                "AM2301": {
                    "Temperature": 72.0,
                    "Humidity": 50.0,
                    "DewPoint": 52.0,
                }
            }
        })
        dht.updateInfo(payload, "tele/bedroom/dht/stat/STATUS10")

        assert dht.setDriver.call_args_list[0] == (("ST", 1),)
        assert dht.setDriver.call_args_list[1] == (("CLITEMP", 72.0),)

    def test_error_and_recovery_workflow(self, full_setup):
        """Test error handling and recovery."""
        dht, _ = full_setup

        # Valid data
        payload = json.dumps({
            "AM2301": {
                "Temperature": 70.0,
                "Humidity": 50.0,
                "DewPoint": 52.0,
            }
        })
        dht.updateInfo(payload, "tele/bedroom/dht/tele/SENSOR")
        assert dht.setDriver.call_args_list[0] == (("ST", 1),)

        dht.setDriver.reset_mock()

        # Error - no sensor data
        payload = json.dumps({"Time": "2025-01-01T12:00:00"})
        dht.updateInfo(payload, "tele/bedroom/dht/tele/SENSOR")
        assert dht.setDriver.call_args_list[0] == (("ST", 0),)

        dht.setDriver.reset_mock()

        # Recovery
        payload = json.dumps({
            "AM2301": {
                "Temperature": 71.0,
                "Humidity": 51.0,
                "DewPoint": 53.0,
            }
        })
        dht.updateInfo(payload, "tele/bedroom/dht/tele/SENSOR")
        assert dht.setDriver.call_args_list[0] == (("ST", 1),)

    def test_humidity_monitoring(self, full_setup):
        """Test humidity monitoring workflow."""
        dht, _ = full_setup

        # Low humidity
        payload = json.dumps({
            "AM2301": {
                "Temperature": 72.0,
                "Humidity": 30.0,
                "DewPoint": 40.0,
            }
        })
        dht.updateInfo(payload, "tele/bedroom/dht/tele/SENSOR")
        assert dht.setDriver.call_args_list[2] == (("CLIHUM", 30.0),)

        dht.setDriver.reset_mock()

        # High humidity
        payload = json.dumps({
            "AM2301": {
                "Temperature": 75.0,
                "Humidity": 80.0,
                "DewPoint": 70.0,
            }
        })
        dht.updateInfo(payload, "tele/bedroom/dht/tele/SENSOR")
        assert dht.setDriver.call_args_list[2] == (("CLIHUM", 80.0),)

    def test_dew_point_tracking(self, full_setup):
        """Test dew point calculation tracking."""
        dht, _ = full_setup

        # Test various dew point scenarios
        payload = json.dumps({
            "AM2301": {
                "Temperature": 80.0,
                "Humidity": 60.0,
                "DewPoint": 65.0,
            }
        })
        dht.updateInfo(payload, "tele/bedroom/dht/tele/SENSOR")
        assert dht.setDriver.call_args_list[3] == (("DEWPT", 65.0),)

    def test_winter_conditions(self, full_setup):
        """Test handling cold winter conditions."""
        dht, _ = full_setup

        payload = json.dumps({
            "AM2301": {
                "Temperature": 32.0,
                "Humidity": 40.0,
                "DewPoint": 10.0,
            }
        })
        dht.updateInfo(payload, "tele/bedroom/dht/tele/SENSOR")

        assert dht.setDriver.call_args_list[1] == (("CLITEMP", 32.0),)
        assert dht.setDriver.call_args_list[3] == (("DEWPT", 10.0),)

    def test_summer_conditions(self, full_setup):
        """Test handling hot summer conditions."""
        dht, _ = full_setup

        payload = json.dumps({
            "AM2301": {
                "Temperature": 95.0,
                "Humidity": 70.0,
                "DewPoint": 85.0,
            }
        })
        dht.updateInfo(payload, "tele/bedroom/dht/tele/SENSOR")

        assert dht.setDriver.call_args_list[1] == (("CLITEMP", 95.0),)
        assert dht.setDriver.call_args_list[2] == (("CLIHUM", 70.0),)

    def test_tasmota_periodic_updates(self, full_setup):
        """Test handling periodic Tasmota telemetry updates."""
        dht, _ = full_setup

        # Simulate regular telemetry updates
        for temp in [70.0, 71.0, 72.0]:
            payload = json.dumps({
                "StatusSNS": {
                    "Time": "2025-01-01T12:00:00",
                    "AM2301": {
                        "Temperature": temp,
                        "Humidity": 50.0,
                        "DewPoint": 52.0,
                    },
                }
            })
            dht.updateInfo(payload, "tele/bedroom/dht/stat/STATUS10")
            dht.setDriver.reset_mock()

        # Last update should have set temperature to 72.0
        payload = json.dumps({
            "StatusSNS": {
                "AM2301": {
                    "Temperature": 72.0,
                    "Humidity": 50.0,
                    "DewPoint": 52.0,
                }
            }
        })
        dht.updateInfo(payload, "tele/bedroom/dht/stat/STATUS10")
        assert dht.setDriver.call_args_list[1] == (("CLITEMP", 72.0),)
