"""
Comprehensive test suite for MQs31 node.

Tests cover:
- Initialization
- JSON payload parsing for energy data
- Power monitoring (current, voltage, power, power factor, total)
- ENERGY key handling
- Query command
- Edge cases and error handling
"""

import json
import pytest
from unittest.mock import Mock
from nodes.MQs31 import MQs31, SENSOR_KEY


class TestMQs31Initialization:
    """Tests for MQs31 initialization."""

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
        return {"cmd_topic": "home/s31/cmd"}

    def test_initialization_basic(self, mock_polyglot, device_config):
        """Test basic MQs31 initialization."""
        s31 = MQs31(
            mock_polyglot, "controller", "s31_1", "S31 Power Monitor", device_config
        )

        assert s31.id == "mqs31"
        assert s31.address == "s31_1"
        assert s31.name == "S31 Power Monitor"
        assert s31.lpfx == "s31_1:S31 Power Monitor"

    def test_initialization_different_name(self, mock_polyglot, device_config):
        """Test initialization with different name."""
        s31 = MQs31(mock_polyglot, "controller", "plug1", "Kitchen Plug", device_config)

        assert s31.lpfx == "plug1:Kitchen Plug"


class TestMQs31UpdateInfo:
    """Tests for updateInfo method (energy data handling)."""

    @pytest.fixture
    def s31_node(self):
        """Create a MQs31 instance for testing."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        poly.getNode = Mock(return_value=Mock())

        device = {"cmd_topic": "test/s31/cmd"}
        node = MQs31(poly, "controller", "s31", "Test", device)
        node.setDriver = Mock()

        return node

    def test_update_info_complete_energy_data(self, s31_node):
        """Test handling complete energy data payload."""
        payload = json.dumps(
            {
                "ENERGY": {
                    "Current": 1.5,
                    "Power": 180.0,
                    "Voltage": 120.0,
                    "Factor": 0.95,
                    "Total": 12.5,
                }
            }
        )

        s31_node.updateInfo(payload, "test/s31/state")

        # Verify all drivers were set
        calls = s31_node.setDriver.call_args_list
        assert len(calls) == 6
        assert calls[0] == (("ST", 1),)
        assert calls[1] == (("CC", 1.5),)
        assert calls[2] == (("CPW", 180.0),)
        assert calls[3] == (("CV", 120.0),)
        assert calls[4] == (("PF", 0.95),)
        assert calls[5] == (("TPW", 12.5),)

    def test_update_info_partial_energy_data(self, s31_node):
        """Test handling partial energy data (some fields missing)."""
        payload = json.dumps({"ENERGY": {"Current": 0.8, "Power": 96.0}})

        s31_node.updateInfo(payload, "test/s31/state")

        # Should set ST to 1 and available fields
        calls = s31_node.setDriver.call_args_list
        assert calls[0] == (("ST", 1),)
        assert calls[1] == (("CC", 0.8),)
        assert calls[2] == (("CPW", 96.0),)
        # Missing fields will get None
        assert calls[3] == (("CV", None),)
        assert calls[4] == (("PF", None),)
        assert calls[5] == (("TPW", None),)

    def test_update_info_zero_values(self, s31_node):
        """Test handling zero energy values (device off)."""
        payload = json.dumps(
            {
                "ENERGY": {
                    "Current": 0.0,
                    "Power": 0,
                    "Voltage": 120.0,
                    "Factor": 0.0,
                    "Total": 15.3,
                }
            }
        )

        s31_node.updateInfo(payload, "test/s31/state")

        calls = s31_node.setDriver.call_args_list
        assert calls[0] == (("ST", 1),)
        assert calls[1] == (("CC", 0.0),)
        assert calls[2] == (("CPW", 0),)

    def test_update_info_no_energy_key(self, s31_node):
        """Test handling payload without ENERGY key."""
        payload = json.dumps({"Temperature": 25, "Humidity": 50})

        s31_node.updateInfo(payload, "test/s31/state")

        # Should set ST to 0 when ENERGY key is missing
        calls = s31_node.setDriver.call_args_list
        assert len(calls) == 1
        assert calls[0] == (("ST", 0),)

    def test_update_info_energy_not_dict(self, s31_node):
        """Test handling ENERGY field that is not a dict."""
        payload = json.dumps({"ENERGY": "not_a_dict"})

        s31_node.updateInfo(payload, "test/s31/state")

        # Should set ST to 0
        calls = s31_node.setDriver.call_args_list
        assert len(calls) == 1
        assert calls[0] == (("ST", 0),)

    def test_update_info_energy_is_none(self, s31_node):
        """Test handling ENERGY field that is None."""
        payload = json.dumps({"ENERGY": None})

        s31_node.updateInfo(payload, "test/s31/state")

        # Should set ST to 0
        calls = s31_node.setDriver.call_args_list
        assert calls[0] == (("ST", 0),)

    def test_update_info_invalid_json(self, s31_node):
        """Test handling invalid JSON payload."""
        payload = "not valid json {"

        s31_node.updateInfo(payload, "test/s31/state")

        # Should not call setDriver due to JSON error
        s31_node.setDriver.assert_not_called()

    def test_update_info_empty_json(self, s31_node):
        """Test handling empty JSON object."""
        payload = json.dumps({})

        s31_node.updateInfo(payload, "test/s31/state")

        # Should set ST to 0
        calls = s31_node.setDriver.call_args_list
        assert calls[0] == (("ST", 0),)

    def test_update_info_empty_energy_dict(self, s31_node):
        """Test handling empty ENERGY dictionary."""
        payload = json.dumps({"ENERGY": {}})

        s31_node.updateInfo(payload, "test/s31/state")

        # Should set ST to 1 but all values will be None
        calls = s31_node.setDriver.call_args_list
        assert calls[0] == (("ST", 1),)
        assert calls[1] == (("CC", None),)
        assert calls[2] == (("CPW", None),)

    def test_update_info_high_power_values(self, s31_node):
        """Test handling high power consumption values."""
        payload = json.dumps(
            {
                "ENERGY": {
                    "Current": 15.0,
                    "Power": 1800.0,
                    "Voltage": 120.0,
                    "Factor": 1.0,
                    "Total": 1234.56,
                }
            }
        )

        s31_node.updateInfo(payload, "test/s31/state")

        calls = s31_node.setDriver.call_args_list
        assert calls[2] == (("CPW", 1800.0),)
        assert calls[5] == (("TPW", 1234.56),)

    def test_update_info_low_power_factor(self, s31_node):
        """Test handling low power factor."""
        payload = json.dumps(
            {
                "ENERGY": {
                    "Current": 2.0,
                    "Power": 100.0,
                    "Voltage": 120.0,
                    "Factor": 0.42,
                    "Total": 5.0,
                }
            }
        )

        s31_node.updateInfo(payload, "test/s31/state")

        calls = s31_node.setDriver.call_args_list
        assert calls[4] == (("PF", 0.42),)

    def test_update_info_extra_fields_ignored(self, s31_node):
        """Test that extra fields in payload are ignored."""
        payload = json.dumps(
            {
                "ENERGY": {
                    "Current": 1.0,
                    "Power": 120.0,
                    "Voltage": 120.0,
                    "Factor": 1.0,
                    "Total": 10.0,
                    "ExtraField": "ignored",
                },
                "Time": "2025-01-01T12:00:00",
            }
        )

        s31_node.updateInfo(payload, "test/s31/state")

        # Should process normally, ignoring extra fields
        calls = s31_node.setDriver.call_args_list
        assert len(calls) == 6


class TestMQs31Query:
    """Tests for query command."""

    @pytest.fixture
    def s31_with_report(self):
        """Create a MQs31 with mocked reportDrivers."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        poly.getNode = Mock(return_value=Mock())

        device = {"cmd_topic": "test/cmd"}
        node = MQs31(poly, "controller", "s31", "Test", device)
        node.reportDrivers = Mock()

        return node

    def test_query_command(self, s31_with_report):
        """Test QUERY command."""
        command = {"cmd": "QUERY"}

        s31_with_report.query(command)

        s31_with_report.reportDrivers.assert_called_once()

    def test_query_command_none(self, s31_with_report):
        """Test QUERY command with None parameter."""
        s31_with_report.query(None)

        s31_with_report.reportDrivers.assert_called_once()


class TestMQs31DriversAndCommands:
    """Tests for node configuration."""

    def test_node_id(self):
        """Test node ID is correct."""
        assert MQs31.id == "mqs31"

    def test_drivers_configuration(self):
        """Test drivers are properly configured."""
        assert len(MQs31.drivers) == 6

        # Check each driver
        driver_dict = {d["driver"]: d for d in MQs31.drivers}

        assert driver_dict["ST"]["uom"] == 2
        assert driver_dict["ST"]["name"] == "Status"

        assert driver_dict["CC"]["uom"] == 1  # ampere
        assert driver_dict["CC"]["name"] == "Current"

        assert driver_dict["CPW"]["uom"] == 73  # watt
        assert driver_dict["CPW"]["name"] == "Power"

        assert driver_dict["CV"]["uom"] == 72  # volt
        assert driver_dict["CV"]["name"] == "Voltage"

        assert driver_dict["PF"]["uom"] == 53  # power factor
        assert driver_dict["PF"]["name"] == "Power Factor"

        assert driver_dict["TPW"]["uom"] == 33  # kWh
        assert driver_dict["TPW"]["name"] == "Total Power"

    def test_commands_configuration(self):
        """Test commands are properly configured."""
        assert "QUERY" in MQs31.commands
        assert MQs31.commands["QUERY"] == MQs31.query

    def test_sensor_key_constant(self):
        """Test SENSOR_KEY constant."""
        assert SENSOR_KEY == "ENERGY"


class TestMQs31Integration:
    """Integration tests for complete workflows."""

    @pytest.fixture
    def full_setup(self):
        """Create a fully mocked setup."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        poly.getNode = Mock(return_value=Mock())

        device = {"cmd_topic": "home/s31/cmnd"}
        node = MQs31(poly, "controller", "s31_kitchen", "Kitchen Plug", device)
        node.setDriver = Mock()
        node.reportDrivers = Mock()

        return node

    def test_device_power_on_workflow(self, full_setup):
        """Test workflow when device powers on."""
        s31 = full_setup

        # Device off
        payload = json.dumps(
            {
                "ENERGY": {
                    "Current": 0.0,
                    "Power": 0,
                    "Voltage": 120.0,
                    "Factor": 0.0,
                    "Total": 10.0,
                }
            }
        )
        s31.updateInfo(payload, "home/s31/tele/SENSOR")

        assert s31.setDriver.call_args_list[0] == (("ST", 1),)
        assert s31.setDriver.call_args_list[2] == (("CPW", 0),)

        s31.setDriver.reset_mock()

        # Device on - load detected
        payload = json.dumps(
            {
                "ENERGY": {
                    "Current": 5.0,
                    "Power": 600.0,
                    "Voltage": 120.0,
                    "Factor": 1.0,
                    "Total": 10.5,
                }
            }
        )
        s31.updateInfo(payload, "home/s31/tele/SENSOR")

        assert s31.setDriver.call_args_list[2] == (("CPW", 600.0),)
        assert s31.setDriver.call_args_list[5] == (("TPW", 10.5),)

    def test_power_monitoring_workflow(self, full_setup):
        """Test continuous power monitoring."""
        s31 = full_setup

        # Initial reading
        payload = json.dumps(
            {
                "ENERGY": {
                    "Current": 2.0,
                    "Power": 240.0,
                    "Voltage": 120.0,
                    "Factor": 1.0,
                    "Total": 5.0,
                }
            }
        )
        s31.updateInfo(payload, "home/s31/tele/SENSOR")

        assert s31.setDriver.call_args_list[1] == (("CC", 2.0),)
        s31.setDriver.reset_mock()

        # Updated reading - power increased
        payload = json.dumps(
            {
                "ENERGY": {
                    "Current": 3.5,
                    "Power": 420.0,
                    "Voltage": 120.0,
                    "Factor": 1.0,
                    "Total": 5.1,
                }
            }
        )
        s31.updateInfo(payload, "home/s31/tele/SENSOR")

        assert s31.setDriver.call_args_list[1] == (("CC", 3.5),)
        assert s31.setDriver.call_args_list[2] == (("CPW", 420.0),)

    def test_query_workflow(self, full_setup):
        """Test query command workflow."""
        s31 = full_setup

        # Update with data
        payload = json.dumps(
            {
                "ENERGY": {
                    "Current": 1.0,
                    "Power": 120.0,
                    "Voltage": 120.0,
                    "Factor": 1.0,
                    "Total": 2.0,
                }
            }
        )
        s31.updateInfo(payload, "home/s31/state")

        # Query current state
        s31.query({"cmd": "QUERY"})

        s31.reportDrivers.assert_called_once()

    def test_error_and_recovery_workflow(self, full_setup):
        """Test error handling and recovery."""
        s31 = full_setup

        # Valid data
        payload = json.dumps(
            {
                "ENERGY": {
                    "Current": 1.0,
                    "Power": 120.0,
                    "Voltage": 120.0,
                    "Factor": 1.0,
                    "Total": 1.0,
                }
            }
        )
        s31.updateInfo(payload, "home/s31/state")
        assert s31.setDriver.call_args_list[0] == (("ST", 1),)

        s31.setDriver.reset_mock()

        # Error - no ENERGY data
        payload = json.dumps({"Temperature": 25})
        s31.updateInfo(payload, "home/s31/state")
        assert s31.setDriver.call_args_list[0] == (("ST", 0),)

        s31.setDriver.reset_mock()

        # Recovery
        payload = json.dumps(
            {
                "ENERGY": {
                    "Current": 1.0,
                    "Power": 120.0,
                    "Voltage": 120.0,
                    "Factor": 1.0,
                    "Total": 1.1,
                }
            }
        )
        s31.updateInfo(payload, "home/s31/state")
        assert s31.setDriver.call_args_list[0] == (("ST", 1),)

    def test_long_term_monitoring_workflow(self, full_setup):
        """Test long-term total power accumulation."""
        s31 = full_setup

        # Day 1
        payload = json.dumps(
            {
                "ENERGY": {
                    "Current": 1.0,
                    "Power": 120.0,
                    "Voltage": 120.0,
                    "Factor": 1.0,
                    "Total": 0.5,
                }
            }
        )
        s31.updateInfo(payload, "home/s31/state")
        assert s31.setDriver.call_args_list[5] == (("TPW", 0.5),)

        s31.setDriver.reset_mock()

        # Day 7
        payload = json.dumps(
            {
                "ENERGY": {
                    "Current": 1.0,
                    "Power": 120.0,
                    "Voltage": 120.0,
                    "Factor": 1.0,
                    "Total": 20.16,
                }
            }
        )
        s31.updateInfo(payload, "home/s31/state")
        assert s31.setDriver.call_args_list[5] == (("TPW", 20.16),)
