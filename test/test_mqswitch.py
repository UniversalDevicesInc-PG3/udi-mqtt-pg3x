"""
Comprehensive test suite for MQSwitch node.

Tests cover:
- Initialization
- MQTT message handling (ON/OFF/UNKNOWN)
- Command handlers (DON/DOF/QUERY)
- State tracking
- Edge cases
"""

import pytest
from unittest.mock import Mock
from nodes.MQSwitch import MQSwitch, ON, OFF, UNKNOWN


class TestMQSwitchInitialization:
    """Tests for MQSwitch initialization."""

    @pytest.fixture
    def mock_polyglot(self):
        """Create a mock polyglot interface."""
        poly = Mock()
        poly.getNode = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])  # Required for Node init
        poly.subscribe = Mock()  # Required for Node init
        return poly

    @pytest.fixture
    def device_config(self):
        """Create a sample device configuration."""
        return {"cmd_topic": "home/switch/1/cmd", "state_topic": "home/switch/1/state"}

    def test_initialization_basic(self, mock_polyglot, device_config):
        """Test basic MQSwitch initialization."""
        controller = Mock()
        mock_polyglot.getNode.return_value = controller

        switch = MQSwitch(
            mock_polyglot, "controller", "switch_1", "Living Room Switch", device_config
        )

        assert switch.id == "MQSW"
        assert switch.address == "switch_1"
        assert switch.name == "Living Room Switch"
        assert switch.cmd_topic == "home/switch/1/cmd"
        assert switch.on_state is False
        assert switch.lpfx == "switch_1:Living Room Switch"

    def test_initialization_gets_controller(self, mock_polyglot, device_config):
        """Test that initialization retrieves the controller."""
        controller = Mock()
        mock_polyglot.getNode.return_value = controller

        switch = MQSwitch(
            mock_polyglot, "controller", "switch_1", "Test Switch", device_config
        )

        mock_polyglot.getNode.assert_called_once_with("controller")
        assert switch.controller == controller

    def test_initialization_with_different_topic(self, mock_polyglot):
        """Test initialization with different MQTT topics."""
        device = {"cmd_topic": "custom/topic/command"}
        controller = Mock()
        mock_polyglot.getNode.return_value = controller

        switch = MQSwitch(mock_polyglot, "controller", "switch_2", "Switch", device)

        assert switch.cmd_topic == "custom/topic/command"


class TestMQSwitchUpdateInfo:
    """Tests for updateInfo method (MQTT message handling)."""

    @pytest.fixture
    def switch(self):
        """Create a MQSwitch instance for testing."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/switch/cmd"}
        sw = MQSwitch(poly, "controller", "sw1", "Test", device)
        sw.setDriver = Mock()
        sw.reportCmd = Mock()

        return sw

    def test_update_info_on_message(self, switch):
        """Test handling ON message."""
        switch.updateInfo("ON", "test/switch/state")

        switch.setDriver.assert_called_once_with("ST", ON)
        switch.reportCmd.assert_called_once_with("DON")
        assert switch.on_state is True

    def test_update_info_on_lowercase(self, switch):
        """Test handling lowercase 'on' message."""
        switch.updateInfo("on", "test/switch/state")

        switch.setDriver.assert_called_once_with("ST", ON)
        switch.reportCmd.assert_called_once_with("DON")
        assert switch.on_state is True

    def test_update_info_on_mixed_case(self, switch):
        """Test handling mixed case 'On' message."""
        switch.updateInfo("On", "test/switch/state")

        switch.setDriver.assert_called_once_with("ST", ON)
        assert switch.on_state is True

    def test_update_info_off_message(self, switch):
        """Test handling OFF message."""
        # Set initial state to on
        switch.on_state = True

        switch.updateInfo("OFF", "test/switch/state")

        switch.setDriver.assert_called_once_with("ST", OFF)
        switch.reportCmd.assert_called_once_with("DOF")
        assert switch.on_state is False

    def test_update_info_off_lowercase(self, switch):
        """Test handling lowercase 'off' message."""
        switch.on_state = True

        switch.updateInfo("off", "test/switch/state")

        switch.setDriver.assert_called_once_with("ST", OFF)
        switch.reportCmd.assert_called_once_with("DOF")
        assert switch.on_state is False

    def test_update_info_unknown_payload(self, switch):
        """Test handling unknown payload."""
        switch.updateInfo("INVALID", "test/switch/state")

        switch.setDriver.assert_called_once_with("ST", UNKNOWN)
        # Should not report DON or DOF for unknown
        switch.reportCmd.assert_not_called()

    def test_update_info_empty_payload(self, switch):
        """Test handling empty payload."""
        switch.updateInfo("", "test/switch/state")

        switch.setDriver.assert_called_once_with("ST", UNKNOWN)
        switch.reportCmd.assert_not_called()

    def test_update_info_on_when_already_on(self, switch):
        """Test receiving ON when already in ON state."""
        switch.on_state = True

        switch.updateInfo("ON", "test/switch/state")

        switch.setDriver.assert_called_once_with("ST", ON)
        # Should not report DON again if already on
        switch.reportCmd.assert_not_called()

    def test_update_info_off_when_already_off(self, switch):
        """Test receiving OFF when already in OFF state."""
        switch.on_state = False

        switch.updateInfo("OFF", "test/switch/state")

        switch.setDriver.assert_called_once_with("ST", OFF)
        # Should not report DOF again if already off
        switch.reportCmd.assert_not_called()

    def test_update_info_state_transitions(self, switch):
        """Test multiple state transitions."""
        # OFF -> ON
        switch.updateInfo("ON", "test/switch/state")
        assert switch.on_state is True

        # ON -> OFF
        switch.updateInfo("OFF", "test/switch/state")
        assert switch.on_state is False

        # OFF -> ON again
        switch.updateInfo("ON", "test/switch/state")
        assert switch.on_state is True


class TestMQSwitchCommands:
    """Tests for command handlers."""

    @pytest.fixture
    def switch_with_controller(self):
        """Create a MQSwitch with mocked controller."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/switch/cmd"}
        sw = MQSwitch(poly, "controller", "sw1", "Test", device)

        return sw

    def test_cmd_on(self, switch_with_controller):
        """Test DON command handler."""
        command = {"cmd": "DON"}

        switch_with_controller.cmd_on(command)

        switch_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/switch/cmd", "ON"
        )

    def test_cmd_off(self, switch_with_controller):
        """Test DOF command handler."""
        command = {"cmd": "DOF"}

        switch_with_controller.cmd_off(command)

        switch_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/switch/cmd", "OFF"
        )

    def test_cmd_on_does_not_change_state_directly(self, switch_with_controller):
        """Test that cmd_on doesn't change on_state directly."""
        initial_state = switch_with_controller.on_state

        switch_with_controller.cmd_on({"cmd": "DON"})

        # State should not change until updateInfo is called
        assert switch_with_controller.on_state == initial_state

    def test_cmd_off_does_not_change_state_directly(self, switch_with_controller):
        """Test that cmd_off doesn't change on_state directly."""
        switch_with_controller.on_state = True
        initial_state = switch_with_controller.on_state

        switch_with_controller.cmd_off({"cmd": "DOF"})

        # State should not change until updateInfo is called
        assert switch_with_controller.on_state == initial_state

    def test_query_command(self, switch_with_controller):
        """Test QUERY command handler."""
        switch_with_controller.reportDrivers = Mock()
        command = {"cmd": "QUERY"}

        switch_with_controller.query(command)

        # Should publish empty message to request state
        switch_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/switch/cmd", ""
        )
        # Should report current drivers
        switch_with_controller.reportDrivers.assert_called_once()

    def test_query_without_command(self, switch_with_controller):
        """Test QUERY with None command."""
        switch_with_controller.reportDrivers = Mock()

        switch_with_controller.query(None)

        switch_with_controller.controller.mqtt_pub.assert_called_once()
        switch_with_controller.reportDrivers.assert_called_once()


class TestMQSwitchDriversAndCommands:
    """Tests for node configuration (drivers, commands, etc.)."""

    def test_node_id(self):
        """Test that node ID is correct."""
        assert MQSwitch.id == "MQSW"

    def test_drivers_configuration(self):
        """Test drivers are properly configured."""
        assert hasattr(MQSwitch, "drivers")
        assert len(MQSwitch.drivers) == 1

        driver = MQSwitch.drivers[0]
        assert driver["driver"] == "ST"
        assert driver["value"] == OFF
        assert driver["uom"] == 78
        assert driver["name"] == "Power"

    def test_commands_configuration(self):
        """Test commands are properly configured."""
        assert hasattr(MQSwitch, "commands")
        assert "DON" in MQSwitch.commands
        assert "DOF" in MQSwitch.commands
        assert "QUERY" in MQSwitch.commands

        assert MQSwitch.commands["DON"] == MQSwitch.cmd_on
        assert MQSwitch.commands["DOF"] == MQSwitch.cmd_off
        assert MQSwitch.commands["QUERY"] == MQSwitch.query

    def test_hint_value(self):
        """Test hint is defined."""
        assert hasattr(MQSwitch, "hint")
        assert MQSwitch.hint == "0x01040200"


class TestMQSwitchConstants:
    """Tests for module constants."""

    def test_constants_values(self):
        """Test that constants have expected values."""
        assert OFF == 0
        assert ON == 100
        assert UNKNOWN == 101

    def test_constants_are_distinct(self):
        """Test that all constants have unique values."""
        assert OFF != ON
        assert OFF != UNKNOWN
        assert ON != UNKNOWN


class TestMQSwitchIntegration:
    """Integration tests for complete workflows."""

    @pytest.fixture
    def full_switch_setup(self):
        """Create a fully mocked switch setup."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "home/light/cmd"}
        sw = MQSwitch(poly, "controller", "light1", "Kitchen Light", device)
        sw.setDriver = Mock()
        sw.reportCmd = Mock()
        sw.reportDrivers = Mock()

        return sw

    def test_full_on_workflow(self, full_switch_setup):
        """Test complete ON workflow: command -> MQTT -> update."""
        switch = full_switch_setup

        # 1. User sends DON command via ISY
        switch.cmd_on({"cmd": "DON"})

        # Verify MQTT publish
        switch.controller.mqtt_pub.assert_called_with("home/light/cmd", "ON")

        # 2. MQTT broker echoes back the state
        switch.updateInfo("ON", "home/light/state")

        # Verify state updated
        assert switch.on_state is True
        switch.setDriver.assert_called_with("ST", ON)
        switch.reportCmd.assert_called_with("DON")

    def test_full_off_workflow(self, full_switch_setup):
        """Test complete OFF workflow: command -> MQTT -> update."""
        switch = full_switch_setup
        switch.on_state = True  # Start in ON state

        # 1. User sends DOF command via ISY
        switch.cmd_off({"cmd": "DOF"})

        # Verify MQTT publish
        switch.controller.mqtt_pub.assert_called_with("home/light/cmd", "OFF")

        # 2. MQTT broker echoes back the state
        switch.updateInfo("OFF", "home/light/state")

        # Verify state updated
        assert switch.on_state is False
        switch.setDriver.assert_called_with("ST", OFF)
        switch.reportCmd.assert_called_with("DOF")

    def test_query_workflow(self, full_switch_setup):
        """Test query workflow."""
        switch = full_switch_setup

        # Query current state
        switch.query(None)

        # Should request update via empty message
        switch.controller.mqtt_pub.assert_called_with("home/light/cmd", "")
        switch.reportDrivers.assert_called_once()

    def test_external_state_change(self, full_switch_setup):
        """Test handling external state change (not from ISY)."""
        switch = full_switch_setup

        # External device (e.g., physical button) turns on the switch
        switch.updateInfo("ON", "home/light/state")

        # Should update ISY to reflect new state
        assert switch.on_state is True
        switch.setDriver.assert_called_with("ST", ON)
        switch.reportCmd.assert_called_with("DON")
