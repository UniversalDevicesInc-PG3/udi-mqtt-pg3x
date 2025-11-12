"""
Comprehensive test suite for MQFan node.

Tests cover:
- Initialization
- MQTT message handling (JSON payloads with FanSpeed)
- Command handlers (DON/DOF/FDUP/FDDOWN/QUERY)
- State tracking and transitions
- Edge cases and error handling
"""

import pytest
from unittest.mock import Mock
from nodes.MQFan import MQFan, FAN_OFF, FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_MAX


class TestMQFanInitialization:
    """Tests for MQFan initialization."""

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
        return {"cmd_topic": "home/fan/1/cmd"}

    def test_initialization_basic(self, mock_polyglot, device_config):
        """Test basic MQFan initialization."""
        controller = Mock()
        mock_polyglot.getNode.return_value = controller

        fan = MQFan(
            mock_polyglot, "controller", "fan_1", "Living Room Fan", device_config
        )

        assert fan.id == "mqfan"
        assert fan.address == "fan_1"
        assert fan.name == "Living Room Fan"
        assert fan.cmd_topic == "home/fan/1/cmd"
        assert fan.fan_speed == FAN_OFF
        assert fan.lpfx == "fan_1:Living Room Fan"

    def test_initialization_gets_controller(self, mock_polyglot, device_config):
        """Test that initialization retrieves the controller."""
        controller = Mock()
        mock_polyglot.getNode.return_value = controller

        fan = MQFan(mock_polyglot, "controller", "fan_1", "Test Fan", device_config)

        mock_polyglot.getNode.assert_called_once_with("controller")
        assert fan.controller == controller

    def test_initialization_with_different_topic(self, mock_polyglot):
        """Test initialization with different MQTT topic."""
        device = {"cmd_topic": "custom/topic/fan/command"}
        controller = Mock()
        mock_polyglot.getNode.return_value = controller

        fan = MQFan(mock_polyglot, "controller", "fan_2", "Fan", device)

        assert fan.cmd_topic == "custom/topic/fan/command"


class TestMQFanUpdateInfo:
    """Tests for updateInfo method (MQTT message handling)."""

    @pytest.fixture
    def fan(self):
        """Create a MQFan instance for testing."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/fan/cmd"}
        f = MQFan(poly, "controller", "fan1", "Test", device)
        f.setDriver = Mock()
        f.reportCmd = Mock()

        return f

    def test_update_info_off_to_low(self, fan):
        """Test transition from OFF to LOW speed."""
        payload = '{"FanSpeed": 1}'
        fan.updateInfo(payload, "test/fan/state")

        fan.setDriver.assert_called_once_with("ST", FAN_LOW)
        fan.reportCmd.assert_called_once_with("DON")
        assert fan.fan_speed == FAN_LOW

    def test_update_info_off_to_medium(self, fan):
        """Test transition from OFF to MEDIUM speed."""
        payload = '{"FanSpeed": 2}'
        fan.updateInfo(payload, "test/fan/state")

        fan.setDriver.assert_called_once_with("ST", FAN_MEDIUM)
        fan.reportCmd.assert_called_once_with("DON")
        assert fan.fan_speed == FAN_MEDIUM

    def test_update_info_off_to_high(self, fan):
        """Test transition from OFF to HIGH speed."""
        payload = '{"FanSpeed": 3}'
        fan.updateInfo(payload, "test/fan/state")

        fan.setDriver.assert_called_once_with("ST", FAN_HIGH)
        fan.reportCmd.assert_called_once_with("DON")
        assert fan.fan_speed == FAN_HIGH

    def test_update_info_to_off(self, fan):
        """Test transition to OFF from running state."""
        fan.fan_speed = FAN_HIGH
        payload = '{"FanSpeed": 0}'
        fan.updateInfo(payload, "test/fan/state")

        fan.setDriver.assert_called_once_with("ST", FAN_OFF)
        fan.reportCmd.assert_called_once_with("DOF")
        assert fan.fan_speed == FAN_OFF

    def test_update_info_speed_change_while_running(self, fan):
        """Test changing speed while fan is already running."""
        fan.fan_speed = FAN_LOW
        payload = '{"FanSpeed": 3}'
        fan.updateInfo(payload, "test/fan/state")

        fan.setDriver.assert_called_once_with("ST", FAN_HIGH)
        # Should not report DON when already on
        fan.reportCmd.assert_not_called()
        assert fan.fan_speed == FAN_HIGH

    def test_update_info_same_speed_no_report(self, fan):
        """Test receiving same speed doesn't trigger reportCmd."""
        fan.fan_speed = FAN_MEDIUM
        payload = '{"FanSpeed": 2}'
        fan.updateInfo(payload, "test/fan/state")

        fan.setDriver.assert_called_once_with("ST", FAN_MEDIUM)
        fan.reportCmd.assert_not_called()

    def test_update_info_invalid_json(self, fan):
        """Test handling invalid JSON payload."""
        payload = "not valid json{"
        initial_speed = fan.fan_speed

        fan.updateInfo(payload, "test/fan/state")

        # Should not change state
        assert fan.fan_speed == initial_speed
        fan.setDriver.assert_not_called()
        fan.reportCmd.assert_not_called()

    def test_update_info_missing_fanspeed_key(self, fan):
        """Test handling JSON without FanSpeed key."""
        payload = '{"Speed": 2}'
        initial_speed = fan.fan_speed

        fan.updateInfo(payload, "test/fan/state")

        assert fan.fan_speed == initial_speed
        fan.setDriver.assert_not_called()

    def test_update_info_fanspeed_not_integer(self, fan):
        """Test handling non-integer FanSpeed value."""
        payload = '{"FanSpeed": "high"}'
        initial_speed = fan.fan_speed

        fan.updateInfo(payload, "test/fan/state")

        assert fan.fan_speed == initial_speed
        fan.setDriver.assert_not_called()

    def test_update_info_fanspeed_negative(self, fan):
        """Test handling negative FanSpeed value."""
        payload = '{"FanSpeed": -1}'
        initial_speed = fan.fan_speed

        fan.updateInfo(payload, "test/fan/state")

        assert fan.fan_speed == initial_speed
        fan.setDriver.assert_not_called()

    def test_update_info_fanspeed_too_high(self, fan):
        """Test handling FanSpeed value above maximum."""
        payload = '{"FanSpeed": 10}'
        initial_speed = fan.fan_speed

        fan.updateInfo(payload, "test/fan/state")

        assert fan.fan_speed == initial_speed
        fan.setDriver.assert_not_called()

    def test_update_info_fanspeed_float(self, fan):
        """Test handling float FanSpeed value."""
        payload = '{"FanSpeed": 2.5}'
        fan.updateInfo(payload, "test/fan/state")

        # Should convert to int
        fan.setDriver.assert_called_once_with("ST", 2)
        assert fan.fan_speed == 2

    def test_update_info_zero_speed_when_already_off(self, fan):
        """Test receiving OFF when already in OFF state."""
        fan.fan_speed = FAN_OFF
        payload = '{"FanSpeed": 0}'

        fan.updateInfo(payload, "test/fan/state")

        fan.setDriver.assert_called_once_with("ST", FAN_OFF)
        # Should not report DOF again if already off
        fan.reportCmd.assert_not_called()

    def test_update_info_multiple_transitions(self, fan):
        """Test multiple state transitions."""
        # OFF -> LOW
        fan.updateInfo('{"FanSpeed": 1}', "test/fan/state")
        assert fan.fan_speed == FAN_LOW

        # LOW -> HIGH
        fan.updateInfo('{"FanSpeed": 3}', "test/fan/state")
        assert fan.fan_speed == FAN_HIGH

        # HIGH -> OFF
        fan.updateInfo('{"FanSpeed": 0}', "test/fan/state")
        assert fan.fan_speed == FAN_OFF


class TestMQFanSetOn:
    """Tests for set_on command handler."""

    @pytest.fixture
    def fan_with_controller(self):
        """Create a MQFan with mocked controller."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/fan/cmd"}
        f = MQFan(poly, "controller", "fan1", "Test", device)
        f.setDriver = Mock()

        return f

    def test_set_on_with_low_speed(self, fan_with_controller):
        """Test DON command with LOW speed."""
        command = {"value": 1}

        fan_with_controller.set_on(command)

        assert fan_with_controller.fan_speed == FAN_LOW
        fan_with_controller.setDriver.assert_called_once_with("ST", FAN_LOW)
        fan_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/fan/cmd", FAN_LOW
        )

    def test_set_on_with_medium_speed(self, fan_with_controller):
        """Test DON command with MEDIUM speed."""
        command = {"value": 2}

        fan_with_controller.set_on(command)

        assert fan_with_controller.fan_speed == FAN_MEDIUM
        fan_with_controller.setDriver.assert_called_once_with("ST", FAN_MEDIUM)
        fan_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/fan/cmd", FAN_MEDIUM
        )

    def test_set_on_with_high_speed(self, fan_with_controller):
        """Test DON command with HIGH speed."""
        command = {"value": 3}

        fan_with_controller.set_on(command)

        assert fan_with_controller.fan_speed == FAN_HIGH
        fan_with_controller.setDriver.assert_called_once_with("ST", FAN_HIGH)
        fan_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/fan/cmd", FAN_HIGH
        )

    def test_set_on_no_value_defaults_to_high(self, fan_with_controller):
        """Test DON command without value defaults to HIGH."""
        command = {}

        fan_with_controller.set_on(command)

        assert fan_with_controller.fan_speed == FAN_HIGH
        fan_with_controller.setDriver.assert_called_once_with("ST", FAN_HIGH)

    def test_set_on_invalid_value_defaults_to_high(self, fan_with_controller):
        """Test DON command with invalid value defaults to HIGH."""
        command = {"value": "invalid"}

        fan_with_controller.set_on(command)

        assert fan_with_controller.fan_speed == FAN_HIGH
        fan_with_controller.setDriver.assert_called_once_with("ST", FAN_HIGH)

    def test_set_on_negative_value_defaults_to_high(self, fan_with_controller):
        """Test DON command with negative value defaults to HIGH."""
        command = {"value": -5}

        fan_with_controller.set_on(command)

        assert fan_with_controller.fan_speed == FAN_HIGH

    def test_set_on_too_high_value_defaults_to_high(self, fan_with_controller):
        """Test DON command with out-of-range value defaults to HIGH."""
        command = {"value": 10}

        fan_with_controller.set_on(command)

        assert fan_with_controller.fan_speed == FAN_HIGH

    def test_set_on_string_number(self, fan_with_controller):
        """Test DON command with string number value."""
        command = {"value": "2"}

        fan_with_controller.set_on(command)

        assert fan_with_controller.fan_speed == FAN_MEDIUM


class TestMQFanSetOff:
    """Tests for set_off command handler."""

    @pytest.fixture
    def fan_with_controller(self):
        """Create a MQFan with mocked controller."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/fan/cmd"}
        f = MQFan(poly, "controller", "fan1", "Test", device)
        f.setDriver = Mock()

        return f

    def test_set_off(self, fan_with_controller):
        """Test DOF command turns fan off."""
        fan_with_controller.fan_speed = FAN_HIGH
        command = {"cmd": "DOF"}

        fan_with_controller.set_off(command)

        assert fan_with_controller.fan_speed == FAN_OFF
        fan_with_controller.setDriver.assert_called_once_with("ST", FAN_OFF)
        fan_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/fan/cmd", FAN_OFF
        )

    def test_set_off_when_already_off(self, fan_with_controller):
        """Test DOF command when fan is already off."""
        fan_with_controller.fan_speed = FAN_OFF
        command = {"cmd": "DOF"}

        fan_with_controller.set_off(command)

        assert fan_with_controller.fan_speed == FAN_OFF
        fan_with_controller.setDriver.assert_called_once_with("ST", FAN_OFF)


class TestMQFanSpeedControl:
    """Tests for speed_up and speed_down command handlers."""

    @pytest.fixture
    def fan_with_controller(self):
        """Create a MQFan with mocked controller."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/fan/cmd"}
        f = MQFan(poly, "controller", "fan1", "Test", device)

        return f

    def test_speed_up(self, fan_with_controller):
        """Test FDUP command sends increment signal."""
        command = {"cmd": "FDUP"}

        fan_with_controller.speed_up(command)

        fan_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/fan/cmd", "+"
        )

    def test_speed_down(self, fan_with_controller):
        """Test FDDOWN command sends decrement signal."""
        command = {"cmd": "FDDOWN"}

        fan_with_controller.speed_down(command)

        fan_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/fan/cmd", "-"
        )

    def test_speed_commands_dont_change_local_state(self, fan_with_controller):
        """Test that speed up/down don't change local state directly."""
        initial_speed = fan_with_controller.fan_speed

        fan_with_controller.speed_up({"cmd": "FDUP"})
        assert fan_with_controller.fan_speed == initial_speed

        fan_with_controller.speed_down({"cmd": "FDDOWN"})
        assert fan_with_controller.fan_speed == initial_speed


class TestMQFanQuery:
    """Tests for query command handler."""

    @pytest.fixture
    def fan_with_controller(self):
        """Create a MQFan with mocked controller."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/fan/cmd"}
        f = MQFan(poly, "controller", "fan1", "Test", device)
        f.reportDrivers = Mock()

        return f

    def test_query_command(self, fan_with_controller):
        """Test QUERY command handler."""
        command = {"cmd": "QUERY"}

        fan_with_controller.query(command)

        fan_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/fan/cmd", ""
        )
        fan_with_controller.reportDrivers.assert_called_once()

    def test_query_without_command(self, fan_with_controller):
        """Test QUERY with None command."""
        fan_with_controller.query(None)

        fan_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/fan/cmd", ""
        )
        fan_with_controller.reportDrivers.assert_called_once()


class TestMQFanDriversAndCommands:
    """Tests for node configuration (drivers, commands, etc.)."""

    def test_node_id(self):
        """Test that node ID is correct."""
        assert MQFan.id == "mqfan"

    def test_drivers_configuration(self):
        """Test drivers are properly configured."""
        assert hasattr(MQFan, "drivers")
        assert len(MQFan.drivers) == 1

        driver = MQFan.drivers[0]
        assert driver["driver"] == "ST"
        assert driver["value"] == FAN_OFF
        assert driver["uom"] == 25
        assert driver["name"] == "Power"

    def test_commands_configuration(self):
        """Test commands are properly configured."""
        assert hasattr(MQFan, "commands")
        assert "QUERY" in MQFan.commands
        assert "DON" in MQFan.commands
        assert "DOF" in MQFan.commands
        assert "FDUP" in MQFan.commands
        assert "FDDOWN" in MQFan.commands

        assert MQFan.commands["QUERY"] == MQFan.query
        assert MQFan.commands["DON"] == MQFan.set_on
        assert MQFan.commands["DOF"] == MQFan.set_off
        assert MQFan.commands["FDUP"] == MQFan.speed_up
        assert MQFan.commands["FDDOWN"] == MQFan.speed_down

    def test_hint_value(self):
        """Test hint is defined."""
        assert hasattr(MQFan, "hint")
        assert MQFan.hint == "0x01040200"


class TestMQFanConstants:
    """Tests for module constants."""

    def test_constants_values(self):
        """Test that constants have expected values."""
        assert FAN_OFF == 0
        assert FAN_LOW == 1
        assert FAN_MEDIUM == 2
        assert FAN_HIGH == 3
        assert FAN_MAX == 3

    def test_constants_are_ordered(self):
        """Test that fan speed constants are properly ordered."""
        assert FAN_OFF < FAN_LOW < FAN_MEDIUM <= FAN_HIGH
        assert FAN_HIGH == FAN_MAX


class TestMQFanIntegration:
    """Integration tests for complete workflows."""

    @pytest.fixture
    def full_fan_setup(self):
        """Create a fully mocked fan setup."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "home/bedroom/fan/cmd"}
        f = MQFan(poly, "controller", "fan1", "Bedroom Fan", device)
        f.setDriver = Mock()
        f.reportCmd = Mock()
        f.reportDrivers = Mock()

        return f

    def test_full_on_workflow(self, full_fan_setup):
        """Test complete ON workflow: command -> MQTT -> update."""
        fan = full_fan_setup

        # User sends DON command with HIGH speed via ISY
        fan.set_on({"value": 3})

        # Verify MQTT publish
        fan.controller.mqtt_pub.assert_called_with("home/bedroom/fan/cmd", FAN_HIGH)
        assert fan.fan_speed == FAN_HIGH

        # MQTT broker echoes back the state
        fan.updateInfo('{"FanSpeed": 3}', "home/bedroom/fan/state")

        # Verify state confirmed
        fan.setDriver.assert_called_with("ST", FAN_HIGH)

    def test_full_off_workflow(self, full_fan_setup):
        """Test complete OFF workflow: command -> MQTT -> update."""
        fan = full_fan_setup
        # Set fan to running state first via updateInfo to ensure proper state tracking
        fan.updateInfo('{"FanSpeed": 2}', "home/bedroom/fan/state")
        fan.reportCmd.reset_mock()  # Reset to clear the DON call

        # User sends DOF command via ISY
        fan.set_off({"cmd": "DOF"})

        # Verify MQTT publish
        fan.controller.mqtt_pub.assert_called_with("home/bedroom/fan/cmd", FAN_OFF)
        assert fan.fan_speed == FAN_OFF

        # MQTT broker echoes back the state
        # Note: Since set_off already changed fan_speed to OFF, updateInfo won't trigger DOF again
        fan.updateInfo('{"FanSpeed": 0}', "home/bedroom/fan/state")

        # Verify state confirmed
        fan.setDriver.assert_called_with("ST", FAN_OFF)
        # reportCmd("DOF") is not called because fan_speed was already set to OFF by set_off

    def test_speed_change_workflow(self, full_fan_setup):
        """Test speed change while fan is running."""
        fan = full_fan_setup

        # Start at LOW
        fan.set_on({"value": 1})
        fan.updateInfo('{"FanSpeed": 1}', "home/bedroom/fan/state")
        assert fan.fan_speed == FAN_LOW

        # Change to HIGH
        fan.set_on({"value": 3})
        fan.updateInfo('{"FanSpeed": 3}', "home/bedroom/fan/state")
        assert fan.fan_speed == FAN_HIGH

    def test_query_workflow(self, full_fan_setup):
        """Test query workflow."""
        fan = full_fan_setup

        # Query current state
        fan.query(None)

        # Should request update via empty message
        fan.controller.mqtt_pub.assert_called_with("home/bedroom/fan/cmd", "")
        fan.reportDrivers.assert_called_once()

    def test_external_state_change(self, full_fan_setup):
        """Test handling external state change (not from ISY)."""
        fan = full_fan_setup

        # External device (e.g., wall switch) turns on the fan
        fan.updateInfo('{"FanSpeed": 2}', "home/bedroom/fan/state")

        # Should update ISY to reflect new state
        assert fan.fan_speed == FAN_MEDIUM
        fan.setDriver.assert_called_with("ST", FAN_MEDIUM)
        fan.reportCmd.assert_called_with("DON")

    def test_speed_up_down_workflow(self, full_fan_setup):
        """Test speed up/down workflow."""
        fan = full_fan_setup
        fan.fan_speed = FAN_MEDIUM

        # User presses speed up button
        fan.speed_up({"cmd": "FDUP"})
        fan.controller.mqtt_pub.assert_called_with("home/bedroom/fan/cmd", "+")

        # Device responds with new speed
        fan.updateInfo('{"FanSpeed": 3}', "home/bedroom/fan/state")
        assert fan.fan_speed == FAN_HIGH

        # User presses speed down button
        fan.speed_down({"cmd": "FDDOWN"})
        fan.controller.mqtt_pub.assert_called_with("home/bedroom/fan/cmd", "-")

        # Device responds with new speed
        fan.updateInfo('{"FanSpeed": 2}', "home/bedroom/fan/state")
        assert fan.fan_speed == FAN_MEDIUM

    def test_error_recovery_workflow(self, full_fan_setup):
        """Test error recovery from invalid messages."""
        fan = full_fan_setup
        fan.fan_speed = FAN_LOW

        # Receive invalid JSON
        fan.updateInfo("invalid json", "home/bedroom/fan/state")

        # State should remain unchanged
        assert fan.fan_speed == FAN_LOW

        # Valid update should still work
        fan.updateInfo('{"FanSpeed": 3}', "home/bedroom/fan/state")
        assert fan.fan_speed == FAN_HIGH
