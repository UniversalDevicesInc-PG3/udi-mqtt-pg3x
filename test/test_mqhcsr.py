"""
Comprehensive test suite for MQhcsr node.

Tests cover:
- Initialization
- JSON payload parsing for ultrasonic distance sensor
- HC-SR04 sensor data handling
- Distance measurement in centimeters
- Query command
- Edge cases and error handling
"""

import json
import pytest
from unittest.mock import Mock
from nodes.MQhcsr import MQhcsr, SENSOR_KEY


class TestMQhcsrInitialization:
    """Tests for MQhcsr initialization."""

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
        return {"cmd_topic": "home/hcsr/cmd"}

    def test_initialization_basic(self, mock_polyglot, device_config):
        """Test basic MQhcsr initialization."""
        hcsr = MQhcsr(
            mock_polyglot, "controller", "hcsr_1", "Ultrasonic Sensor", device_config
        )

        assert hcsr.id == "mqhcsr"
        assert hcsr.address == "hcsr_1"
        assert hcsr.name == "Ultrasonic Sensor"
        assert hcsr.lpfx == "hcsr_1:Ultrasonic Sensor"

    def test_initialization_different_name(self, mock_polyglot, device_config):
        """Test initialization with different name."""
        hcsr = MQhcsr(
            mock_polyglot,
            "controller",
            "garage_sensor",
            "Garage Distance",
            device_config,
        )

        assert hcsr.lpfx == "garage_sensor:Garage Distance"


class TestMQhcsrUpdateInfo:
    """Tests for updateInfo method (distance sensor data handling)."""

    @pytest.fixture
    def hcsr_node(self):
        """Create a MQhcsr instance for testing."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        poly.getNode = Mock(return_value=Mock())

        device = {"cmd_topic": "test/hcsr/cmd"}
        node = MQhcsr(poly, "controller", "hcsr", "Test", device)
        node.setDriver = Mock()

        return node

    def test_update_info_valid_distance(self, hcsr_node):
        """Test handling valid distance measurement."""
        payload = json.dumps({"SR04": {"Distance": 50}})

        hcsr_node.updateInfo(payload, "test/hcsr/state")

        calls = hcsr_node.setDriver.call_args_list
        assert len(calls) == 2
        assert calls[0] == (("ST", 1),)
        assert calls[1] == (("DISTANC", 50),)

    def test_update_info_zero_distance(self, hcsr_node):
        """Test handling zero distance (object very close)."""
        payload = json.dumps({"SR04": {"Distance": 0}})

        hcsr_node.updateInfo(payload, "test/hcsr/state")

        calls = hcsr_node.setDriver.call_args_list
        assert calls[0] == (("ST", 1),)
        assert calls[1] == (("DISTANC", 0),)

    def test_update_info_max_distance(self, hcsr_node):
        """Test handling maximum distance measurement."""
        payload = json.dumps({"SR04": {"Distance": 400}})

        hcsr_node.updateInfo(payload, "test/hcsr/state")

        calls = hcsr_node.setDriver.call_args_list
        assert calls[0] == (("ST", 1),)
        assert calls[1] == (("DISTANC", 400),)

    def test_update_info_decimal_distance(self, hcsr_node):
        """Test handling decimal distance values."""
        payload = json.dumps({"SR04": {"Distance": 25.5}})

        hcsr_node.updateInfo(payload, "test/hcsr/state")

        calls = hcsr_node.setDriver.call_args_list
        assert calls[0] == (("ST", 1),)
        assert calls[1] == (("DISTANC", 25.5),)

    def test_update_info_no_sr04_key(self, hcsr_node):
        """Test handling payload without SR04 key."""
        payload = json.dumps({"Temperature": 25, "Humidity": 50})

        hcsr_node.updateInfo(payload, "test/hcsr/state")

        calls = hcsr_node.setDriver.call_args_list
        assert len(calls) == 2
        assert calls[0] == (("ST", 0),)
        assert calls[1] == (("DISTANC", 0),)

    def test_update_info_sr04_not_dict(self, hcsr_node):
        """Test handling SR04 field that is not a dict."""
        payload = json.dumps({"SR04": "not_a_dict"})

        hcsr_node.updateInfo(payload, "test/hcsr/state")

        calls = hcsr_node.setDriver.call_args_list
        assert calls[0] == (("ST", 0),)
        assert calls[1] == (("DISTANC", 0),)

    def test_update_info_sr04_is_none(self, hcsr_node):
        """Test handling SR04 field that is None."""
        payload = json.dumps({"SR04": None})

        hcsr_node.updateInfo(payload, "test/hcsr/state")

        calls = hcsr_node.setDriver.call_args_list
        assert calls[0] == (("ST", 0),)
        assert calls[1] == (("DISTANC", 0),)

    def test_update_info_no_distance_key(self, hcsr_node):
        """Test handling SR04 dict without Distance key."""
        payload = json.dumps({"SR04": {"Other": 123}})

        hcsr_node.updateInfo(payload, "test/hcsr/state")

        calls = hcsr_node.setDriver.call_args_list
        assert calls[0] == (("ST", 0),)
        assert calls[1] == (("DISTANC", 0),)

    def test_update_info_distance_is_none(self, hcsr_node):
        """Test handling Distance value that is None."""
        payload = json.dumps({"SR04": {"Distance": None}})

        hcsr_node.updateInfo(payload, "test/hcsr/state")

        calls = hcsr_node.setDriver.call_args_list
        assert calls[0] == (("ST", 0),)
        assert calls[1] == (("DISTANC", 0),)

    def test_update_info_invalid_json(self, hcsr_node):
        """Test handling invalid JSON payload."""
        payload = "not valid json {"

        hcsr_node.updateInfo(payload, "test/hcsr/state")

        hcsr_node.setDriver.assert_not_called()

    def test_update_info_empty_json(self, hcsr_node):
        """Test handling empty JSON object."""
        payload = json.dumps({})

        hcsr_node.updateInfo(payload, "test/hcsr/state")

        calls = hcsr_node.setDriver.call_args_list
        assert calls[0] == (("ST", 0),)
        assert calls[1] == (("DISTANC", 0),)

    def test_update_info_empty_sr04_dict(self, hcsr_node):
        """Test handling empty SR04 dictionary."""
        payload = json.dumps({"SR04": {}})

        hcsr_node.updateInfo(payload, "test/hcsr/state")

        calls = hcsr_node.setDriver.call_args_list
        assert calls[0] == (("ST", 0),)
        assert calls[1] == (("DISTANC", 0),)

    def test_update_info_negative_distance(self, hcsr_node):
        """Test handling negative distance (sensor error)."""
        payload = json.dumps({"SR04": {"Distance": -1}})

        hcsr_node.updateInfo(payload, "test/hcsr/state")

        # Should still set the value even if negative
        calls = hcsr_node.setDriver.call_args_list
        assert calls[0] == (("ST", 1),)
        assert calls[1] == (("DISTANC", -1),)

    def test_update_info_extra_fields_ignored(self, hcsr_node):
        """Test that extra fields in payload are ignored."""
        payload = json.dumps(
            {
                "SR04": {"Distance": 75, "ExtraField": "ignored", "Other": 999},
                "Time": "2025-01-01T12:00:00",
            }
        )

        hcsr_node.updateInfo(payload, "test/hcsr/state")

        calls = hcsr_node.setDriver.call_args_list
        assert len(calls) == 2
        assert calls[1] == (("DISTANC", 75),)

    def test_update_info_typical_ranges(self, hcsr_node):
        """Test handling typical HC-SR04 measurement ranges."""
        # Very close - 2cm (minimum range)
        payload = json.dumps({"SR04": {"Distance": 2}})
        hcsr_node.updateInfo(payload, "test/hcsr/state")
        assert hcsr_node.setDriver.call_args_list[1] == (("DISTANC", 2),)

        hcsr_node.setDriver.reset_mock()

        # Medium range - 100cm
        payload = json.dumps({"SR04": {"Distance": 100}})
        hcsr_node.updateInfo(payload, "test/hcsr/state")
        assert hcsr_node.setDriver.call_args_list[1] == (("DISTANC", 100),)

        hcsr_node.setDriver.reset_mock()

        # Maximum range - 400cm (maximum range)
        payload = json.dumps({"SR04": {"Distance": 400}})
        hcsr_node.updateInfo(payload, "test/hcsr/state")
        assert hcsr_node.setDriver.call_args_list[1] == (("DISTANC", 400),)


class TestMQhcsrQuery:
    """Tests for query command."""

    @pytest.fixture
    def hcsr_with_report(self):
        """Create a MQhcsr with mocked reportDrivers."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        poly.getNode = Mock(return_value=Mock())

        device = {"cmd_topic": "test/cmd"}
        node = MQhcsr(poly, "controller", "hcsr", "Test", device)
        node.reportDrivers = Mock()

        return node

    def test_query_command(self, hcsr_with_report):
        """Test QUERY command."""
        command = {"cmd": "QUERY"}

        hcsr_with_report.query(command)

        hcsr_with_report.reportDrivers.assert_called_once()

    def test_query_command_none(self, hcsr_with_report):
        """Test QUERY command with None parameter."""
        hcsr_with_report.query(None)

        hcsr_with_report.reportDrivers.assert_called_once()


class TestMQhcsrDriversAndCommands:
    """Tests for node configuration."""

    def test_node_id(self):
        """Test node ID is correct."""
        assert MQhcsr.id == "mqhcsr"

    def test_drivers_configuration(self):
        """Test drivers are properly configured."""
        assert len(MQhcsr.drivers) == 2

        driver_dict = {d["driver"]: d for d in MQhcsr.drivers}

        assert driver_dict["ST"]["uom"] == 2  # boolean
        assert driver_dict["ST"]["name"] == "Status"

        assert driver_dict["DISTANC"]["uom"] == 5  # centimeter
        assert driver_dict["DISTANC"]["name"] == "Distance"

    def test_commands_configuration(self):
        """Test commands are properly configured."""
        assert "QUERY" in MQhcsr.commands
        assert MQhcsr.commands["QUERY"] == MQhcsr.query

    def test_sensor_key_constant(self):
        """Test SENSOR_KEY constant."""
        assert SENSOR_KEY == "SR04"


class TestMQhcsrIntegration:
    """Integration tests for complete workflows."""

    @pytest.fixture
    def full_setup(self):
        """Create a fully mocked setup."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        poly.getNode = Mock(return_value=Mock())

        device = {"cmd_topic": "home/garage/hcsr/cmnd"}
        node = MQhcsr(poly, "controller", "hcsr_garage", "Garage Distance", device)
        node.setDriver = Mock()
        node.reportDrivers = Mock()

        return node

    def test_distance_monitoring_workflow(self, full_setup):
        """Test continuous distance monitoring."""
        hcsr = full_setup

        # Car far away
        payload = json.dumps({"SR04": {"Distance": 300}})
        hcsr.updateInfo(payload, "home/garage/hcsr/tele/SENSOR")

        assert hcsr.setDriver.call_args_list[0] == (("ST", 1),)
        assert hcsr.setDriver.call_args_list[1] == (("DISTANC", 300),)

        hcsr.setDriver.reset_mock()

        # Car approaching
        payload = json.dumps({"SR04": {"Distance": 150}})
        hcsr.updateInfo(payload, "home/garage/hcsr/tele/SENSOR")

        assert hcsr.setDriver.call_args_list[1] == (("DISTANC", 150),)

        hcsr.setDriver.reset_mock()

        # Car at optimal stop position
        payload = json.dumps({"SR04": {"Distance": 50}})
        hcsr.updateInfo(payload, "home/garage/hcsr/tele/SENSOR")

        assert hcsr.setDriver.call_args_list[1] == (("DISTANC", 50),)

    def test_garage_door_use_case(self, full_setup):
        """Test garage door parking assistant use case."""
        hcsr = full_setup

        # Garage empty
        payload = json.dumps({"SR04": {"Distance": 400}})
        hcsr.updateInfo(payload, "home/garage/hcsr/state")
        assert hcsr.setDriver.call_args_list[1] == (("DISTANC", 400),)

        hcsr.setDriver.reset_mock()

        # Car entering
        payload = json.dumps({"SR04": {"Distance": 200}})
        hcsr.updateInfo(payload, "home/garage/hcsr/state")
        assert hcsr.setDriver.call_args_list[1] == (("DISTANC", 200),)

        hcsr.setDriver.reset_mock()

        # Car parked
        payload = json.dumps({"SR04": {"Distance": 30}})
        hcsr.updateInfo(payload, "home/garage/hcsr/state")
        assert hcsr.setDriver.call_args_list[1] == (("DISTANC", 30),)

    def test_query_workflow(self, full_setup):
        """Test query command workflow."""
        hcsr = full_setup

        # Update with distance
        payload = json.dumps({"SR04": {"Distance": 100}})
        hcsr.updateInfo(payload, "home/garage/hcsr/state")

        # Query current state
        hcsr.query({"cmd": "QUERY"})

        hcsr.reportDrivers.assert_called_once()

    def test_error_and_recovery_workflow(self, full_setup):
        """Test error handling and recovery."""
        hcsr = full_setup

        # Valid data
        payload = json.dumps({"SR04": {"Distance": 100}})
        hcsr.updateInfo(payload, "home/garage/hcsr/state")
        assert hcsr.setDriver.call_args_list[0] == (("ST", 1),)
        assert hcsr.setDriver.call_args_list[1] == (("DISTANC", 100),)

        hcsr.setDriver.reset_mock()

        # Error - no SR04 data
        payload = json.dumps({"Temperature": 25})
        hcsr.updateInfo(payload, "home/garage/hcsr/state")
        assert hcsr.setDriver.call_args_list[0] == (("ST", 0),)
        assert hcsr.setDriver.call_args_list[1] == (("DISTANC", 0),)

        hcsr.setDriver.reset_mock()

        # Recovery
        payload = json.dumps({"SR04": {"Distance": 100}})
        hcsr.updateInfo(payload, "home/garage/hcsr/state")
        assert hcsr.setDriver.call_args_list[0] == (("ST", 1),)
        assert hcsr.setDriver.call_args_list[1] == (("DISTANC", 100),)

    def test_sensor_out_of_range_workflow(self, full_setup):
        """Test handling sensor out of range scenarios."""
        hcsr = full_setup

        # Valid measurement
        payload = json.dumps({"SR04": {"Distance": 50}})
        hcsr.updateInfo(payload, "home/garage/hcsr/state")
        assert hcsr.setDriver.call_args_list[1] == (("DISTANC", 50),)

        hcsr.setDriver.reset_mock()

        # Out of range (no echo received) - missing Distance
        payload = json.dumps({"SR04": {}})
        hcsr.updateInfo(payload, "home/garage/hcsr/state")
        assert hcsr.setDriver.call_args_list[0] == (("ST", 0),)
        assert hcsr.setDriver.call_args_list[1] == (("DISTANC", 0),)

        hcsr.setDriver.reset_mock()

        # Back in range
        payload = json.dumps({"SR04": {"Distance": 75}})
        hcsr.updateInfo(payload, "home/garage/hcsr/state")
        assert hcsr.setDriver.call_args_list[0] == (("ST", 1),)
        assert hcsr.setDriver.call_args_list[1] == (("DISTANC", 75),)

    def test_water_level_monitoring(self, full_setup):
        """Test water level monitoring use case."""
        hcsr = full_setup

        # Tank nearly empty (sensor at top, water far down)
        payload = json.dumps({"SR04": {"Distance": 380}})
        hcsr.updateInfo(payload, "home/water/hcsr/state")
        assert hcsr.setDriver.call_args_list[1] == (("DISTANC", 380),)

        hcsr.setDriver.reset_mock()

        # Tank half full
        payload = json.dumps({"SR04": {"Distance": 200}})
        hcsr.updateInfo(payload, "home/water/hcsr/state")
        assert hcsr.setDriver.call_args_list[1] == (("DISTANC", 200),)

        hcsr.setDriver.reset_mock()

        # Tank nearly full
        payload = json.dumps({"SR04": {"Distance": 10}})
        hcsr.updateInfo(payload, "home/water/hcsr/state")
        assert hcsr.setDriver.call_args_list[1] == (("DISTANC", 10),)
