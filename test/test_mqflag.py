"""
Comprehensive test suite for MQFlag node.

Tests cover:
- Initialization
- MQTT message handling with all valid payloads
- Invalid payload handling
- Reset command
- Query command
- Edge cases
"""

import pytest
from unittest.mock import Mock
from nodes.MQFlag import MQFlag, PAYLOAD_MAP, ERROR_STATE


class TestMQFlagInitialization:
    """Tests for MQFlag initialization."""

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
        return {"cmd_topic": "home/flag/1/cmd"}

    def test_initialization_basic(self, mock_polyglot, device_config):
        """Test basic MQFlag initialization."""
        controller = Mock()
        mock_polyglot.getNode.return_value = controller

        flag = MQFlag(mock_polyglot, "controller", "flag_1", "Test Flag", device_config)

        assert flag.id == "mqflag"
        assert flag.address == "flag_1"
        assert flag.name == "Test Flag"
        assert flag.cmd_topic == "home/flag/1/cmd"
        assert flag.lpfx == "flag_1:Test Flag"

    def test_initialization_gets_controller(self, mock_polyglot, device_config):
        """Test that initialization retrieves the controller."""
        controller = Mock()
        mock_polyglot.getNode.return_value = controller

        flag = MQFlag(mock_polyglot, "controller", "flag_1", "Test", device_config)

        mock_polyglot.getNode.assert_called_once_with("controller")
        assert flag.controller == controller

    def test_initialization_with_different_topic(self, mock_polyglot):
        """Test initialization with different MQTT topic."""
        device = {"cmd_topic": "custom/device/flag"}
        controller = Mock()
        mock_polyglot.getNode.return_value = controller

        flag = MQFlag(mock_polyglot, "controller", "flag_2", "Flag", device)

        assert flag.cmd_topic == "custom/device/flag"


class TestMQFlagUpdateInfo:
    """Tests for updateInfo method (MQTT message handling)."""

    @pytest.fixture
    def flag(self):
        """Create a MQFlag instance for testing."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/flag/cmd"}
        f = MQFlag(poly, "controller", "flag1", "Test", device)
        f.setDriver = Mock()
        f.reportCmd = Mock()

        return f

    def test_update_info_ok_payload(self, flag):
        """Test handling OK payload."""
        flag.updateInfo("OK", "test/flag/state")

        flag.setDriver.assert_called_once_with("ST", PAYLOAD_MAP["OK"])
        flag.reportCmd.assert_called_once_with("DON")

    def test_update_info_nok_payload(self, flag):
        """Test handling NOK payload."""
        flag.updateInfo("NOK", "test/flag/state")

        flag.setDriver.assert_called_once_with("ST", PAYLOAD_MAP["NOK"])
        flag.reportCmd.assert_called_once_with("DON")

    def test_update_info_lo_payload(self, flag):
        """Test handling LO payload."""
        flag.updateInfo("LO", "test/flag/state")

        flag.setDriver.assert_called_once_with("ST", PAYLOAD_MAP["LO"])
        flag.reportCmd.assert_called_once_with("DON")

    def test_update_info_hi_payload(self, flag):
        """Test handling HI payload."""
        flag.updateInfo("HI", "test/flag/state")

        flag.setDriver.assert_called_once_with("ST", PAYLOAD_MAP["HI"])
        flag.reportCmd.assert_called_once_with("DON")

    def test_update_info_err_payload(self, flag):
        """Test handling ERR payload."""
        flag.updateInfo("ERR", "test/flag/state")

        flag.setDriver.assert_called_once_with("ST", PAYLOAD_MAP["ERR"])
        flag.reportCmd.assert_called_once_with("DON")

    def test_update_info_in_payload(self, flag):
        """Test handling IN payload."""
        flag.updateInfo("IN", "test/flag/state")

        flag.setDriver.assert_called_once_with("ST", PAYLOAD_MAP["IN"])
        flag.reportCmd.assert_called_once_with("DON")

    def test_update_info_out_payload(self, flag):
        """Test handling OUT payload."""
        flag.updateInfo("OUT", "test/flag/state")

        flag.setDriver.assert_called_once_with("ST", PAYLOAD_MAP["OUT"])
        flag.reportCmd.assert_called_once_with("DON")

    def test_update_info_up_payload(self, flag):
        """Test handling UP payload."""
        flag.updateInfo("UP", "test/flag/state")

        flag.setDriver.assert_called_once_with("ST", PAYLOAD_MAP["UP"])
        flag.reportCmd.assert_called_once_with("DON")

    def test_update_info_down_payload(self, flag):
        """Test handling DOWN payload."""
        flag.updateInfo("DOWN", "test/flag/state")

        flag.setDriver.assert_called_once_with("ST", PAYLOAD_MAP["DOWN"])
        flag.reportCmd.assert_called_once_with("DON")

    def test_update_info_trigger_payload(self, flag):
        """Test handling TRIGGER payload."""
        flag.updateInfo("TRIGGER", "test/flag/state")

        flag.setDriver.assert_called_once_with("ST", PAYLOAD_MAP["TRIGGER"])
        flag.reportCmd.assert_called_once_with("DON")

    def test_update_info_on_payload(self, flag):
        """Test handling ON payload."""
        flag.updateInfo("ON", "test/flag/state")

        flag.setDriver.assert_called_once_with("ST", PAYLOAD_MAP["ON"])
        flag.reportCmd.assert_called_once_with("DON")

    def test_update_info_off_payload(self, flag):
        """Test handling OFF payload."""
        flag.updateInfo("OFF", "test/flag/state")

        flag.setDriver.assert_called_once_with("ST", PAYLOAD_MAP["OFF"])
        flag.reportCmd.assert_called_once_with("DON")

    def test_update_info_dash_payload(self, flag):
        """Test handling --- (dash) payload."""
        flag.updateInfo("---", "test/flag/state")

        flag.setDriver.assert_called_once_with("ST", PAYLOAD_MAP["---"])
        flag.reportCmd.assert_called_once_with("DON")

    def test_update_info_invalid_payload(self, flag):
        """Test handling invalid payload."""
        flag.updateInfo("INVALID", "test/flag/state")

        flag.setDriver.assert_called_once_with("ST", ERROR_STATE)
        flag.reportCmd.assert_called_once_with("DON")

    def test_update_info_empty_payload(self, flag):
        """Test handling empty payload."""
        flag.updateInfo("", "test/flag/state")

        flag.setDriver.assert_called_once_with("ST", ERROR_STATE)
        flag.reportCmd.assert_called_once_with("DON")

    def test_update_info_lowercase_payload(self, flag):
        """Test handling lowercase payload (should fail)."""
        flag.updateInfo("ok", "test/flag/state")

        # Lowercase should be treated as invalid
        flag.setDriver.assert_called_once_with("ST", ERROR_STATE)
        flag.reportCmd.assert_called_once_with("DON")

    def test_update_info_all_payloads_unique(self, flag):
        """Test that all valid payloads map to different states."""
        states_seen = set()

        for payload in PAYLOAD_MAP.keys():
            flag.setDriver.reset_mock()
            flag.updateInfo(payload, "test/flag/state")

            # Get the state value that was set
            state = flag.setDriver.call_args[0][1]
            assert state not in states_seen, f"Duplicate state for {payload}"
            states_seen.add(state)


class TestMQFlagCommands:
    """Tests for command handlers."""

    @pytest.fixture
    def flag_with_controller(self):
        """Create a MQFlag with mocked controller."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/flag/cmd"}
        f = MQFlag(poly, "controller", "flag1", "Test", device)
        f.reportCmd = Mock()
        f.reportDrivers = Mock()

        return f

    def test_reset_command(self, flag_with_controller):
        """Test RESET command handler."""
        command = {"cmd": "RESET"}

        flag_with_controller.reset_send(command)

        flag_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/flag/cmd", "RESET"
        )
        flag_with_controller.reportCmd.assert_called_once_with("DOF")

    def test_query_command(self, flag_with_controller):
        """Test QUERY command handler."""
        command = {"cmd": "QUERY"}

        flag_with_controller.query(command)

        # Should publish empty message to request state
        flag_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/flag/cmd", ""
        )
        # Should report current drivers
        flag_with_controller.reportDrivers.assert_called_once()

    def test_query_without_command(self, flag_with_controller):
        """Test QUERY with None command."""
        flag_with_controller.query(None)

        flag_with_controller.controller.mqtt_pub.assert_called_once()
        flag_with_controller.reportDrivers.assert_called_once()


class TestMQFlagDriversAndCommands:
    """Tests for node configuration (drivers, commands, etc.)."""

    def test_node_id(self):
        """Test that node ID is correct."""
        assert MQFlag.id == "mqflag"

    def test_drivers_configuration(self):
        """Test drivers are properly configured."""
        assert hasattr(MQFlag, "drivers")
        assert len(MQFlag.drivers) == 1

        driver = MQFlag.drivers[0]
        assert driver["driver"] == "ST"
        assert driver["value"] == 0
        assert driver["uom"] == 25
        assert driver["name"] == "Status"

    def test_commands_configuration(self):
        """Test commands are properly configured."""
        assert hasattr(MQFlag, "commands")
        assert "QUERY" in MQFlag.commands
        assert "RESET" in MQFlag.commands

        assert MQFlag.commands["QUERY"] == MQFlag.query
        assert MQFlag.commands["RESET"] == MQFlag.reset_send

    def test_hint_value(self):
        """Test hint is defined."""
        assert hasattr(MQFlag, "hint")
        assert MQFlag.hint == "0x01010000"


class TestMQFlagConstants:
    """Tests for module constants."""

    def test_payload_map_completeness(self):
        """Test that PAYLOAD_MAP contains all expected keys."""
        expected_keys = [
            "OK",
            "NOK",
            "LO",
            "HI",
            "ERR",
            "IN",
            "OUT",
            "UP",
            "DOWN",
            "TRIGGER",
            "ON",
            "OFF",
            "---",
        ]

        for key in expected_keys:
            assert key in PAYLOAD_MAP, f"Missing key: {key}"

    def test_payload_map_values_unique(self):
        """Test that all PAYLOAD_MAP values are unique."""
        values = list(PAYLOAD_MAP.values())
        assert len(values) == len(set(values)), "PAYLOAD_MAP has duplicate values"

    def test_payload_map_values_sequential(self):
        """Test that PAYLOAD_MAP values are sequential integers."""
        values = sorted(PAYLOAD_MAP.values())
        expected = list(range(len(PAYLOAD_MAP)))
        assert values == expected

    def test_error_state_defined(self):
        """Test that ERROR_STATE is properly defined."""
        assert ERROR_STATE == PAYLOAD_MAP["ERR"]
        assert ERROR_STATE == 4


class TestMQFlagIntegration:
    """Integration tests for complete workflows."""

    @pytest.fixture
    def full_flag_setup(self):
        """Create a fully mocked flag setup."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "home/sensor/flag"}
        f = MQFlag(poly, "controller", "sensor1", "Water Sensor", device)
        f.setDriver = Mock()
        f.reportCmd = Mock()
        f.reportDrivers = Mock()

        return f

    def test_sensor_ok_workflow(self, full_flag_setup):
        """Test sensor reporting OK status."""
        flag = full_flag_setup

        # Sensor reports OK
        flag.updateInfo("OK", "home/sensor/state")

        assert flag.setDriver.called
        flag.setDriver.assert_called_with("ST", 0)
        flag.reportCmd.assert_called_with("DON")

    def test_sensor_error_workflow(self, full_flag_setup):
        """Test sensor reporting error status."""
        flag = full_flag_setup

        # Sensor reports ERR
        flag.updateInfo("ERR", "home/sensor/state")

        flag.setDriver.assert_called_with("ST", 4)
        flag.reportCmd.assert_called_with("DON")

    def test_sensor_level_transitions(self, full_flag_setup):
        """Test sensor level transitions (LO -> OK -> HI)."""
        flag = full_flag_setup

        # Low level
        flag.updateInfo("LO", "home/sensor/state")
        assert flag.setDriver.call_args[0] == ("ST", 2)

        # Normal level
        flag.updateInfo("OK", "home/sensor/state")
        assert flag.setDriver.call_args[0] == ("ST", 0)

        # High level
        flag.updateInfo("HI", "home/sensor/state")
        assert flag.setDriver.call_args[0] == ("ST", 3)

    def test_reset_workflow(self, full_flag_setup):
        """Test reset command workflow."""
        flag = full_flag_setup

        # Send reset command
        flag.reset_send({"cmd": "RESET"})

        flag.controller.mqtt_pub.assert_called_with("home/sensor/flag", "RESET")
        flag.reportCmd.assert_called_with("DOF")

    def test_query_workflow(self, full_flag_setup):
        """Test query workflow."""
        flag = full_flag_setup

        # Query current state
        flag.query(None)

        flag.controller.mqtt_pub.assert_called_with("home/sensor/flag", "")
        flag.reportDrivers.assert_called_once()

    def test_external_state_change(self, full_flag_setup):
        """Test handling external state change."""
        flag = full_flag_setup

        # External condition triggers TRIGGER state
        flag.updateInfo("TRIGGER", "home/sensor/state")

        flag.setDriver.assert_called_with("ST", 9)
        flag.reportCmd.assert_called_with("DON")
