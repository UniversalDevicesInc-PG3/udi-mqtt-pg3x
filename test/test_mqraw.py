"""
Comprehensive test suite for MQraw node.

Tests cover:
- Initialization
- Integer payload parsing
- Invalid payload handling
- Query command
- Multiple drivers (ST and GV1)
- Edge cases
"""

import pytest
from unittest.mock import Mock
from nodes.MQraw import MQraw


class TestMQrawInitialization:
    """Tests for MQraw initialization."""

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
        return {"cmd_topic": "home/raw/1/cmd"}

    def test_initialization_basic(self, mock_polyglot, device_config):
        """Test basic MQraw initialization."""
        raw = MQraw(mock_polyglot, "controller", "raw_1", "Test Raw", device_config)

        assert raw.id == "mqr"
        assert raw.address == "raw_1"
        assert raw.name == "Test Raw"
        assert raw.cmd_topic == "home/raw/1/cmd"
        assert raw.lpfx == "raw_1:Test Raw"

    def test_initialization_with_different_topic(self, mock_polyglot):
        """Test initialization with different MQTT topic."""
        device = {"cmd_topic": "custom/device/raw"}

        raw = MQraw(mock_polyglot, "controller", "raw_2", "Raw", device)

        assert raw.cmd_topic == "custom/device/raw"


class TestMQrawUpdateInfo:
    """Tests for updateInfo method (MQTT message handling)."""

    @pytest.fixture
    def raw_node(self):
        """Create a MQraw instance for testing."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        poly.getNode = Mock()

        device = {"cmd_topic": "test/raw/cmd"}
        node = MQraw(poly, "controller", "raw1", "Test", device)
        node.setDriver = Mock()

        return node

    def test_update_info_positive_integer(self, raw_node):
        """Test handling positive integer payload."""
        raw_node.updateInfo("42", "test/raw/state")

        # Should set ST to 1 (success) and GV1 to the value
        calls = raw_node.setDriver.call_args_list
        assert len(calls) == 2
        assert calls[0] == (("ST", 1),)
        assert calls[1] == (("GV1", 42),)

    def test_update_info_zero(self, raw_node):
        """Test handling zero value."""
        raw_node.updateInfo("0", "test/raw/state")

        calls = raw_node.setDriver.call_args_list
        assert len(calls) == 2
        assert calls[0] == (("ST", 1),)
        assert calls[1] == (("GV1", 0),)

    def test_update_info_negative_integer(self, raw_node):
        """Test handling negative integer payload."""
        raw_node.updateInfo("-15", "test/raw/state")

        calls = raw_node.setDriver.call_args_list
        assert len(calls) == 2
        assert calls[0] == (("ST", 1),)
        assert calls[1] == (("GV1", -15),)

    def test_update_info_large_integer(self, raw_node):
        """Test handling large integer value."""
        raw_node.updateInfo("999999", "test/raw/state")

        calls = raw_node.setDriver.call_args_list
        assert len(calls) == 2
        assert calls[0] == (("ST", 1),)
        assert calls[1] == (("GV1", 999999),)

    def test_update_info_invalid_string(self, raw_node):
        """Test handling invalid string payload."""
        raw_node.updateInfo("not_a_number", "test/raw/state")

        # Should set ST to 0 (error) and GV1 to 0
        calls = raw_node.setDriver.call_args_list
        assert len(calls) == 2
        assert calls[0] == (("ST", 0),)
        assert calls[1] == (("GV1", 0),)

    def test_update_info_empty_string(self, raw_node):
        """Test handling empty string payload."""
        raw_node.updateInfo("", "test/raw/state")

        # Should set ST to 0 (error) and GV1 to 0
        calls = raw_node.setDriver.call_args_list
        assert len(calls) == 2
        assert calls[0] == (("ST", 0),)
        assert calls[1] == (("GV1", 0),)

    def test_update_info_float_string(self, raw_node):
        """Test handling float string (should fail - integers only)."""
        raw_node.updateInfo("3.14", "test/raw/state")

        # Should fail to parse as int and set error state
        calls = raw_node.setDriver.call_args_list
        assert len(calls) == 2
        assert calls[0] == (("ST", 0),)
        assert calls[1] == (("GV1", 0),)

    def test_update_info_integer_with_spaces(self, raw_node):
        """Test handling integer with leading/trailing spaces."""
        raw_node.updateInfo("  123  ", "test/raw/state")

        # int() should handle spaces
        calls = raw_node.setDriver.call_args_list
        assert len(calls) == 2
        assert calls[0] == (("ST", 1),)
        assert calls[1] == (("GV1", 123),)

    def test_update_info_mixed_alphanumeric(self, raw_node):
        """Test handling mixed alphanumeric string."""
        raw_node.updateInfo("123abc", "test/raw/state")

        # Should fail to parse and set error state
        calls = raw_node.setDriver.call_args_list
        assert len(calls) == 2
        assert calls[0] == (("ST", 0),)
        assert calls[1] == (("GV1", 0),)

    def test_update_info_hex_string(self, raw_node):
        """Test handling hexadecimal string."""
        raw_node.updateInfo("0xFF", "test/raw/state")

        # int() without base parameter won't parse hex, should fail
        calls = raw_node.setDriver.call_args_list
        assert len(calls) == 2
        assert calls[0] == (("ST", 0),)
        assert calls[1] == (("GV1", 0),)

    def test_update_info_multiple_values(self, raw_node):
        """Test multiple sequential value updates."""
        # First update
        raw_node.updateInfo("100", "test/raw/state")
        first_calls = raw_node.setDriver.call_args_list.copy()

        # Reset mock for second update
        raw_node.setDriver.reset_mock()

        # Second update
        raw_node.updateInfo("200", "test/raw/state")
        second_calls = raw_node.setDriver.call_args_list

        # Verify first update
        assert first_calls[1] == (("GV1", 100),)

        # Verify second update
        assert second_calls[1] == (("GV1", 200),)

    def test_update_info_success_then_error(self, raw_node):
        """Test successful parse followed by error."""
        # First: successful parse
        raw_node.updateInfo("42", "test/raw/state")
        first_status = raw_node.setDriver.call_args_list[0][0][1]
        assert first_status == 1

        # Reset mock
        raw_node.setDriver.reset_mock()

        # Second: failed parse
        raw_node.updateInfo("invalid", "test/raw/state")
        second_status = raw_node.setDriver.call_args_list[0][0][1]
        assert second_status == 0


class TestMQrawCommands:
    """Tests for command handlers."""

    @pytest.fixture
    def raw_with_controller(self):
        """Create a MQraw with mocked controller."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        poly.getNode = Mock()

        device = {"cmd_topic": "test/raw/cmd"}
        node = MQraw(poly, "controller", "raw1", "Test", device)
        node.reportDrivers = Mock()

        return node

    def test_query_command(self, raw_with_controller):
        """Test QUERY command handler."""
        command = {"cmd": "QUERY"}

        raw_with_controller.query(command)

        # Should report current drivers
        raw_with_controller.reportDrivers.assert_called_once()

    def test_query_without_command(self, raw_with_controller):
        """Test QUERY with None command."""
        raw_with_controller.query(None)

        raw_with_controller.reportDrivers.assert_called_once()


class TestMQrawDriversAndCommands:
    """Tests for node configuration (drivers, commands, etc.)."""

    def test_node_id(self):
        """Test that node ID is correct."""
        assert MQraw.id == "mqr"

    def test_drivers_configuration(self):
        """Test drivers are properly configured."""
        assert hasattr(MQraw, "drivers")
        assert len(MQraw.drivers) == 2

        # Check ST driver
        st_driver = MQraw.drivers[0]
        assert st_driver["driver"] == "ST"
        assert st_driver["value"] == 0
        assert st_driver["uom"] == 2
        assert st_driver["name"] == "Status"

        # Check GV1 driver
        gv1_driver = MQraw.drivers[1]
        assert gv1_driver["driver"] == "GV1"
        assert gv1_driver["value"] == 0
        assert gv1_driver["uom"] == 56
        assert gv1_driver["name"] == "Value"

    def test_commands_configuration(self):
        """Test commands are properly configured."""
        assert hasattr(MQraw, "commands")
        assert "QUERY" in MQraw.commands
        assert MQraw.commands["QUERY"] == MQraw.query

    def test_hint_value(self):
        """Test hint is defined."""
        assert hasattr(MQraw, "hint")
        assert MQraw.hint == "0x01030200"


class TestMQrawIntegration:
    """Integration tests for complete workflows."""

    @pytest.fixture
    def full_raw_setup(self):
        """Create a fully mocked raw setup."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        poly.getNode = Mock()

        device = {"cmd_topic": "home/counter/value"}
        node = MQraw(poly, "controller", "counter1", "Event Counter", device)
        node.setDriver = Mock()
        node.reportDrivers = Mock()

        return node

    def test_counter_workflow(self, full_raw_setup):
        """Test counter incrementing workflow."""
        raw = full_raw_setup

        # Counter starts at 0
        raw.updateInfo("0", "home/counter/state")
        assert raw.setDriver.call_args_list[1] == (("GV1", 0),)

        raw.setDriver.reset_mock()

        # Counter increments
        raw.updateInfo("1", "home/counter/state")
        assert raw.setDriver.call_args_list[1] == (("GV1", 1),)

        raw.setDriver.reset_mock()

        # Counter continues
        raw.updateInfo("2", "home/counter/state")
        assert raw.setDriver.call_args_list[1] == (("GV1", 2),)

    def test_sensor_reading_workflow(self, full_raw_setup):
        """Test sensor reading workflow with various values."""
        raw = full_raw_setup

        # Normal reading
        raw.updateInfo("250", "home/sensor/state")
        assert raw.setDriver.call_args_list[0] == (("ST", 1),)
        assert raw.setDriver.call_args_list[1] == (("GV1", 250),)

        raw.setDriver.reset_mock()

        # High reading
        raw.updateInfo("980", "home/sensor/state")
        assert raw.setDriver.call_args_list[1] == (("GV1", 980),)

        raw.setDriver.reset_mock()

        # Low reading
        raw.updateInfo("10", "home/sensor/state")
        assert raw.setDriver.call_args_list[1] == (("GV1", 10),)

    def test_error_recovery_workflow(self, full_raw_setup):
        """Test error and recovery workflow."""
        raw = full_raw_setup

        # Valid reading
        raw.updateInfo("100", "home/sensor/state")
        assert raw.setDriver.call_args_list[0] == (("ST", 1),)

        raw.setDriver.reset_mock()

        # Error occurs
        raw.updateInfo("ERROR", "home/sensor/state")
        assert raw.setDriver.call_args_list[0] == (("ST", 0),)
        assert raw.setDriver.call_args_list[1] == (("GV1", 0),)

        raw.setDriver.reset_mock()

        # Recovery with valid reading
        raw.updateInfo("105", "home/sensor/state")
        assert raw.setDriver.call_args_list[0] == (("ST", 1),)
        assert raw.setDriver.call_args_list[1] == (("GV1", 105),)

    def test_query_workflow(self, full_raw_setup):
        """Test query workflow."""
        raw = full_raw_setup

        # Query current state
        raw.query(None)

        raw.reportDrivers.assert_called_once()

    def test_negative_values_workflow(self, full_raw_setup):
        """Test handling negative values (e.g., temperature sensor)."""
        raw = full_raw_setup

        # Below zero
        raw.updateInfo("-5", "home/temp/state")
        assert raw.setDriver.call_args_list[0] == (("ST", 1),)
        assert raw.setDriver.call_args_list[1] == (("GV1", -5),)

        raw.setDriver.reset_mock()

        # Deep negative
        raw.updateInfo("-100", "home/temp/state")
        assert raw.setDriver.call_args_list[1] == (("GV1", -100),)
