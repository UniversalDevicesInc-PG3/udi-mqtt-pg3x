"""
Comprehensive test suite for MQDimmer node.

Tests cover:
- Initialization
- MQTT message handling (JSON payloads with Power and Dimmer)
- Command handlers (DON/DOF/BRT/DIM/QUERY)
- State tracking and transitions
- Edge cases and error handling
- Brightness level management
"""

import pytest
from unittest.mock import Mock
from nodes.MQDimmer import MQDimmer, OFF, FULL, INC, DIMLOWERLIMIT


class TestMQDimmerInitialization:
    """Tests for MQDimmer initialization."""

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
        return {
            "cmd_topic": "home/dimmer/1/cmd",
            "status_topic": "home/dimmer/1/status",
        }

    def test_initialization_basic(self, mock_polyglot, device_config):
        """Test basic MQDimmer initialization."""
        controller = Mock()
        mock_polyglot.getNode.return_value = controller

        dimmer = MQDimmer(
            mock_polyglot, "controller", "dimmer_1", "Living Room Dimmer", device_config
        )

        assert dimmer.id == "mqdimmer"
        assert dimmer.address == "dimmer_1"
        assert dimmer.name == "Living Room Dimmer"
        assert dimmer.cmd_topic == "home/dimmer/1/cmd"
        assert dimmer.status_topic == "home/dimmer/1/status"
        assert dimmer.dimmer == OFF
        assert dimmer.lpfx == "dimmer_1:Living Room Dimmer"

    def test_initialization_gets_controller(self, mock_polyglot, device_config):
        """Test that initialization retrieves the controller."""
        controller = Mock()
        mock_polyglot.getNode.return_value = controller

        dimmer = MQDimmer(
            mock_polyglot, "controller", "dimmer_1", "Test Dimmer", device_config
        )

        mock_polyglot.getNode.assert_called_once_with("controller")
        assert dimmer.controller == controller

    def test_initialization_with_different_topics(self, mock_polyglot):
        """Test initialization with different MQTT topics."""
        device = {
            "cmd_topic": "custom/topic/dimmer/command",
            "status_topic": "custom/topic/dimmer/state",
        }
        controller = Mock()
        mock_polyglot.getNode.return_value = controller

        dimmer = MQDimmer(mock_polyglot, "controller", "dimmer_2", "Dimmer", device)

        assert dimmer.cmd_topic == "custom/topic/dimmer/command"
        assert dimmer.status_topic == "custom/topic/dimmer/state"


class TestMQDimmerUpdateInfo:
    """Tests for updateInfo method (MQTT message handling)."""

    @pytest.fixture
    def dimmer(self):
        """Create a MQDimmer instance for testing."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        poly.getNode.return_value = controller

        device = {
            "cmd_topic": "test/dimmer/cmd",
            "status_topic": "test/dimmer/status",
        }
        d = MQDimmer(poly, "controller", "dimmer1", "Test", device)
        d.setDriver = Mock()
        d.reportCmd = Mock()

        return d

    def test_update_info_power_on_with_dimmer_level(self, dimmer):
        """Test receiving power ON with specific dimmer level."""
        payload = '{"POWER": "ON", "Dimmer": 75}'
        dimmer.updateInfo(payload, "test/dimmer/status")

        dimmer.setDriver.assert_called_once_with("ST", 75)
        dimmer.reportCmd.assert_called_once_with("DON")
        assert dimmer.dimmer == 75

    def test_update_info_power_off(self, dimmer):
        """Test receiving power OFF."""
        dimmer.dimmer = 50
        payload = '{"POWER": "OFF"}'
        dimmer.updateInfo(payload, "test/dimmer/status")

        dimmer.setDriver.assert_called_once_with("ST", OFF)
        dimmer.reportCmd.assert_called_once_with("DOF")
        assert dimmer.dimmer == OFF

    def test_update_info_dimmer_only_from_off(self, dimmer):
        """Test receiving dimmer level change from OFF state."""
        payload = '{"Dimmer": 50}'
        dimmer.updateInfo(payload, "test/dimmer/status")

        dimmer.setDriver.assert_called_once_with("ST", 50)
        dimmer.reportCmd.assert_called_once_with("DON")
        assert dimmer.dimmer == 50

    def test_update_info_dimmer_increase(self, dimmer):
        """Test dimmer level increase while on."""
        dimmer.dimmer = 30
        payload = '{"Dimmer": 60}'
        dimmer.updateInfo(payload, "test/dimmer/status")

        dimmer.setDriver.assert_called_once_with("ST", 60)
        dimmer.reportCmd.assert_called_once_with("BRT")
        assert dimmer.dimmer == 60

    def test_update_info_dimmer_decrease(self, dimmer):
        """Test dimmer level decrease while on."""
        dimmer.dimmer = 80
        payload = '{"Dimmer": 40}'
        dimmer.updateInfo(payload, "test/dimmer/status")

        dimmer.setDriver.assert_called_once_with("ST", 40)
        dimmer.reportCmd.assert_called_once_with("DIM")
        assert dimmer.dimmer == 40

    def test_update_info_power_on_no_dimmer_uses_last_level(self, dimmer):
        """Test power ON without dimmer value uses last known level."""
        dimmer.dimmer = 70
        payload = '{"POWER": "ON"}'
        dimmer.updateInfo(payload, "test/dimmer/status")

        # Should maintain last level
        dimmer.setDriver.assert_not_called()
        dimmer.reportCmd.assert_not_called()
        assert dimmer.dimmer == 70

    def test_update_info_power_on_no_dimmer_from_off(self, dimmer):
        """Test power ON without dimmer value when off defaults to FULL."""
        dimmer.dimmer = OFF
        payload = '{"POWER": "ON"}'
        dimmer.updateInfo(payload, "test/dimmer/status")

        dimmer.setDriver.assert_called_once_with("ST", FULL)
        dimmer.reportCmd.assert_called_once_with("DON")
        assert dimmer.dimmer == FULL

    def test_update_info_same_level_no_change(self, dimmer):
        """Test receiving same level doesn't trigger update."""
        dimmer.dimmer = 50
        payload = '{"Dimmer": 50}'
        dimmer.updateInfo(payload, "test/dimmer/status")

        dimmer.setDriver.assert_not_called()
        dimmer.reportCmd.assert_not_called()

    def test_update_info_invalid_json(self, dimmer):
        """Test handling invalid JSON payload."""
        payload = "not valid json{"
        initial_level = dimmer.dimmer

        dimmer.updateInfo(payload, "test/dimmer/status")

        assert dimmer.dimmer == initial_level
        dimmer.setDriver.assert_not_called()
        dimmer.reportCmd.assert_not_called()

    def test_update_info_empty_payload(self, dimmer):
        """Test handling payload with no relevant data."""
        payload = '{"SomeOtherKey": "value"}'
        initial_level = dimmer.dimmer

        dimmer.updateInfo(payload, "test/dimmer/status")

        assert dimmer.dimmer == initial_level
        dimmer.setDriver.assert_not_called()

    def test_update_info_dimmer_not_integer(self, dimmer):
        """Test handling non-integer Dimmer value."""
        payload = '{"Dimmer": "high"}'
        initial_level = dimmer.dimmer

        dimmer.updateInfo(payload, "test/dimmer/status")

        assert dimmer.dimmer == initial_level
        dimmer.setDriver.assert_not_called()

    def test_update_info_dimmer_float(self, dimmer):
        """Test handling float Dimmer value."""
        payload = '{"Dimmer": 75.5}'
        dimmer.updateInfo(payload, "test/dimmer/status")

        # Should convert to int
        dimmer.setDriver.assert_called_once_with("ST", 75)
        assert dimmer.dimmer == 75

    def test_update_info_power_off_when_already_off(self, dimmer):
        """Test receiving OFF when already in OFF state."""
        dimmer.dimmer = OFF
        payload = '{"POWER": "OFF"}'

        dimmer.updateInfo(payload, "test/dimmer/status")

        dimmer.setDriver.assert_not_called()
        dimmer.reportCmd.assert_not_called()

    def test_update_info_multiple_transitions(self, dimmer):
        """Test multiple state transitions."""
        # OFF -> 50
        dimmer.updateInfo('{"Dimmer": 50}', "test/dimmer/status")
        assert dimmer.dimmer == 50

        # 50 -> 80 (brighten)
        dimmer.updateInfo('{"Dimmer": 80}', "test/dimmer/status")
        assert dimmer.dimmer == 80

        # 80 -> 30 (dim)
        dimmer.updateInfo('{"Dimmer": 30}', "test/dimmer/status")
        assert dimmer.dimmer == 30

        # 30 -> OFF
        dimmer.updateInfo('{"POWER": "OFF"}', "test/dimmer/status")
        assert dimmer.dimmer == OFF

    def test_update_info_power_on_with_zero_dimmer(self, dimmer):
        """Test power ON with dimmer level 0 (edge case)."""
        payload = '{"POWER": "ON", "Dimmer": 0}'
        dimmer.updateInfo(payload, "test/dimmer/status")

        # Dimmer level is 0, which is same as initial state, so no change
        dimmer.setDriver.assert_not_called()
        dimmer.reportCmd.assert_not_called()
        assert dimmer.dimmer == OFF


class TestMQDimmerSetDimmerLevel:
    """Tests for internal _set_dimmer_level method."""

    @pytest.fixture
    def dimmer_with_controller(self):
        """Create a MQDimmer with mocked controller."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {
            "cmd_topic": "test/dimmer/cmd",
            "status_topic": "test/dimmer/status",
        }
        d = MQDimmer(poly, "controller", "dimmer1", "Test", device)
        d.setDriver = Mock()

        return d

    def test_set_dimmer_level_valid(self, dimmer_with_controller):
        """Test setting valid dimmer level."""
        dimmer_with_controller._set_dimmer_level(50)

        assert dimmer_with_controller.dimmer == 50
        dimmer_with_controller.setDriver.assert_called_once_with("ST", 50)
        dimmer_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/dimmer/cmd", 50
        )

    def test_set_dimmer_level_clamped_high(self, dimmer_with_controller):
        """Test that level is clamped to FULL."""
        dimmer_with_controller._set_dimmer_level(150)

        assert dimmer_with_controller.dimmer == FULL
        dimmer_with_controller.setDriver.assert_called_once_with("ST", FULL)

    def test_set_dimmer_level_clamped_low(self, dimmer_with_controller):
        """Test that level is clamped to OFF."""
        dimmer_with_controller._set_dimmer_level(-10)

        assert dimmer_with_controller.dimmer == OFF
        dimmer_with_controller.setDriver.assert_called_once_with("ST", OFF)

    def test_set_dimmer_level_without_report(self, dimmer_with_controller):
        """Test setting level without reporting to MQTT."""
        dimmer_with_controller._set_dimmer_level(60, report=False)

        assert dimmer_with_controller.dimmer == 60
        dimmer_with_controller.setDriver.assert_called_once_with("ST", 60)
        dimmer_with_controller.controller.mqtt_pub.assert_not_called()


class TestMQDimmerOnCommand:
    """Tests for on_cmd command handler."""

    @pytest.fixture
    def dimmer_with_controller(self):
        """Create a MQDimmer with mocked controller."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {
            "cmd_topic": "test/dimmer/cmd",
            "status_topic": "test/dimmer/status",
        }
        d = MQDimmer(poly, "controller", "dimmer1", "Test", device)
        d.setDriver = Mock()

        return d

    def test_on_cmd_with_value(self, dimmer_with_controller):
        """Test DON command with specific level."""
        command = {"value": 75}

        dimmer_with_controller.on_cmd(command)

        assert dimmer_with_controller.dimmer == 75
        dimmer_with_controller.setDriver.assert_called_once_with("ST", 75)
        dimmer_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/dimmer/cmd", 75
        )

    def test_on_cmd_without_value_uses_last_level(self, dimmer_with_controller):
        """Test DON command without value uses last level."""
        dimmer_with_controller.dimmer = 60
        command = {}

        dimmer_with_controller.on_cmd(command)

        assert dimmer_with_controller.dimmer == 60
        dimmer_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/dimmer/cmd", 60
        )

    def test_on_cmd_with_zero_defaults_to_inc(self, dimmer_with_controller):
        """Test DON command with value 0 defaults to INC."""
        command = {"value": 0}

        dimmer_with_controller.on_cmd(command)

        assert dimmer_with_controller.dimmer == INC
        dimmer_with_controller.setDriver.assert_called_once_with("ST", INC)

    def test_on_cmd_with_invalid_value_uses_last_level(self, dimmer_with_controller):
        """Test DON command with invalid value uses last level."""
        dimmer_with_controller.dimmer = 50
        command = {"value": "invalid"}

        dimmer_with_controller.on_cmd(command)

        assert dimmer_with_controller.dimmer == 50

    def test_on_cmd_with_string_number(self, dimmer_with_controller):
        """Test DON command with string number value."""
        command = {"value": "80"}

        dimmer_with_controller.on_cmd(command)

        assert dimmer_with_controller.dimmer == 80

    def test_on_cmd_from_off_without_value_defaults_to_inc(
        self, dimmer_with_controller
    ):
        """Test DON command from OFF without value defaults to INC."""
        dimmer_with_controller.dimmer = OFF
        command = {}

        dimmer_with_controller.on_cmd(command)

        assert dimmer_with_controller.dimmer == INC


class TestMQDimmerOffCommand:
    """Tests for off_cmd command handler."""

    @pytest.fixture
    def dimmer_with_controller(self):
        """Create a MQDimmer with mocked controller."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {
            "cmd_topic": "test/dimmer/cmd",
            "status_topic": "test/dimmer/status",
        }
        d = MQDimmer(poly, "controller", "dimmer1", "Test", device)
        d.setDriver = Mock()

        return d

    def test_off_cmd(self, dimmer_with_controller):
        """Test DOF command turns dimmer off."""
        dimmer_with_controller.dimmer = 75
        command = {"cmd": "DOF"}

        dimmer_with_controller.off_cmd(command)

        assert dimmer_with_controller.dimmer == OFF
        dimmer_with_controller.setDriver.assert_called_once_with("ST", OFF)
        dimmer_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/dimmer/cmd", OFF
        )

    def test_off_cmd_when_already_off(self, dimmer_with_controller):
        """Test DOF command when dimmer is already off."""
        dimmer_with_controller.dimmer = OFF
        command = {"cmd": "DOF"}

        dimmer_with_controller.off_cmd(command)

        assert dimmer_with_controller.dimmer == OFF
        dimmer_with_controller.setDriver.assert_called_once_with("ST", OFF)


class TestMQDimmerBrightenCommand:
    """Tests for brt_cmd command handler."""

    @pytest.fixture
    def dimmer_with_controller(self):
        """Create a MQDimmer with mocked controller."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {
            "cmd_topic": "test/dimmer/cmd",
            "status_topic": "test/dimmer/status",
        }
        d = MQDimmer(poly, "controller", "dimmer1", "Test", device)
        d.setDriver = Mock()

        return d

    def test_brt_cmd_increases_by_inc(self, dimmer_with_controller):
        """Test BRT command increases brightness by INC."""
        dimmer_with_controller.dimmer = 40
        command = {"cmd": "BRT"}

        dimmer_with_controller.brt_cmd(command)

        assert dimmer_with_controller.dimmer == 50  # 40 + INC(10)
        dimmer_with_controller.setDriver.assert_called_once_with("ST", 50)

    def test_brt_cmd_at_max_stays_at_full(self, dimmer_with_controller):
        """Test BRT command at max stays at FULL."""
        dimmer_with_controller.dimmer = FULL
        command = {"cmd": "BRT"}

        dimmer_with_controller.brt_cmd(command)

        assert dimmer_with_controller.dimmer == FULL

    def test_brt_cmd_near_max_caps_at_full(self, dimmer_with_controller):
        """Test BRT command near max caps at FULL."""
        dimmer_with_controller.dimmer = 95
        command = {"cmd": "BRT"}

        dimmer_with_controller.brt_cmd(command)

        assert dimmer_with_controller.dimmer == FULL

    def test_brt_cmd_from_zero(self, dimmer_with_controller):
        """Test BRT command from OFF level."""
        dimmer_with_controller.dimmer = OFF
        command = {"cmd": "BRT"}

        dimmer_with_controller.brt_cmd(command)

        assert dimmer_with_controller.dimmer == INC


class TestMQDimmerDimCommand:
    """Tests for dim_cmd command handler."""

    @pytest.fixture
    def dimmer_with_controller(self):
        """Create a MQDimmer with mocked controller."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {
            "cmd_topic": "test/dimmer/cmd",
            "status_topic": "test/dimmer/status",
        }
        d = MQDimmer(poly, "controller", "dimmer1", "Test", device)
        d.setDriver = Mock()

        return d

    def test_dim_cmd_decreases_by_inc(self, dimmer_with_controller):
        """Test DIM command decreases brightness by INC."""
        dimmer_with_controller.dimmer = 50
        command = {"cmd": "DIM"}

        dimmer_with_controller.dim_cmd(command)

        assert dimmer_with_controller.dimmer == 40  # 50 - INC(10)
        dimmer_with_controller.setDriver.assert_called_once_with("ST", 40)

    def test_dim_cmd_at_min_stays_at_off(self, dimmer_with_controller):
        """Test DIM command at min stays at OFF."""
        dimmer_with_controller.dimmer = OFF
        command = {"cmd": "DIM"}

        dimmer_with_controller.dim_cmd(command)

        assert dimmer_with_controller.dimmer == OFF

    def test_dim_cmd_near_min_caps_at_off(self, dimmer_with_controller):
        """Test DIM command near min caps at OFF."""
        dimmer_with_controller.dimmer = 5
        command = {"cmd": "DIM"}

        dimmer_with_controller.dim_cmd(command)

        assert dimmer_with_controller.dimmer == OFF


class TestMQDimmerQuery:
    """Tests for query command handler."""

    @pytest.fixture
    def dimmer_with_controller(self):
        """Create a MQDimmer with mocked controller."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {
            "cmd_topic": "test/dimmer/cmd",
            "status_topic": "test/dimmer/status",
        }
        d = MQDimmer(poly, "controller", "dimmer1", "Test", device)
        d.reportDrivers = Mock()

        return d

    def test_query_command(self, dimmer_with_controller):
        """Test QUERY command handler."""
        command = {"cmd": "QUERY"}

        dimmer_with_controller.query(command)

        # Should publish to State topic (derived from cmd_topic)
        dimmer_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/dimmer/State", ""
        )
        dimmer_with_controller.reportDrivers.assert_called_once()

    def test_query_without_command(self, dimmer_with_controller):
        """Test QUERY with None command."""
        dimmer_with_controller.query(None)

        dimmer_with_controller.controller.mqtt_pub.assert_called_once()
        dimmer_with_controller.reportDrivers.assert_called_once()

    def test_query_topic_construction(self, dimmer_with_controller):
        """Test that query constructs correct topic."""
        dimmer_with_controller.cmd_topic = "home/living/dimmer/cmd"
        dimmer_with_controller.query(None)

        # Should replace last segment with "State"
        dimmer_with_controller.controller.mqtt_pub.assert_called_once_with(
            "home/living/dimmer/State", ""
        )


class TestMQDimmerDriversAndCommands:
    """Tests for node configuration (drivers, commands, etc.)."""

    def test_node_id(self):
        """Test that node ID is correct."""
        assert MQDimmer.id == "mqdimmer"

    def test_drivers_configuration(self):
        """Test drivers are properly configured."""
        assert hasattr(MQDimmer, "drivers")
        assert len(MQDimmer.drivers) == 1

        driver = MQDimmer.drivers[0]
        assert driver["driver"] == "ST"
        assert driver["value"] == OFF
        assert driver["uom"] == 51  # percent
        assert driver["name"] == "Status"

    def test_commands_configuration(self):
        """Test commands are properly configured."""
        assert hasattr(MQDimmer, "commands")
        assert "QUERY" in MQDimmer.commands
        assert "DON" in MQDimmer.commands
        assert "DOF" in MQDimmer.commands
        assert "BRT" in MQDimmer.commands
        assert "DIM" in MQDimmer.commands

        assert MQDimmer.commands["QUERY"] == MQDimmer.query
        assert MQDimmer.commands["DON"] == MQDimmer.on_cmd
        assert MQDimmer.commands["DOF"] == MQDimmer.off_cmd
        assert MQDimmer.commands["BRT"] == MQDimmer.brt_cmd
        assert MQDimmer.commands["DIM"] == MQDimmer.dim_cmd

    def test_hint_value(self):
        """Test hint is defined."""
        assert hasattr(MQDimmer, "hint")
        assert MQDimmer.hint == "0x01020900"


class TestMQDimmerConstants:
    """Tests for module constants."""

    def test_constants_values(self):
        """Test that constants have expected values."""
        assert OFF == 0
        assert FULL == 100
        assert INC == 10
        assert DIMLOWERLIMIT == 10

    def test_constants_are_valid(self):
        """Test that constants are properly ordered."""
        assert OFF < DIMLOWERLIMIT <= INC < FULL


class TestMQDimmerIntegration:
    """Integration tests for complete workflows."""

    @pytest.fixture
    def full_dimmer_setup(self):
        """Create a fully mocked dimmer setup."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {
            "cmd_topic": "home/bedroom/dimmer/cmd",
            "status_topic": "home/bedroom/dimmer/status",
        }
        d = MQDimmer(poly, "controller", "dimmer1", "Bedroom Dimmer", device)
        d.setDriver = Mock()
        d.reportCmd = Mock()
        d.reportDrivers = Mock()

        return d

    def test_full_on_workflow(self, full_dimmer_setup):
        """Test complete ON workflow: command -> MQTT -> update."""
        dimmer = full_dimmer_setup

        # User sends DON command with 80% via ISY
        dimmer.on_cmd({"value": 80})

        # Verify MQTT publish
        dimmer.controller.mqtt_pub.assert_called_with("home/bedroom/dimmer/cmd", 80)
        assert dimmer.dimmer == 80

        # MQTT broker echoes back the state
        dimmer.updateInfo('{"POWER": "ON", "Dimmer": 80}', "home/bedroom/dimmer/status")

        # Verify state confirmed (no change since already set)
        assert dimmer.dimmer == 80

    def test_full_off_workflow(self, full_dimmer_setup):
        """Test complete OFF workflow: command -> MQTT -> update."""
        dimmer = full_dimmer_setup
        # Set dimmer to running state first
        dimmer.updateInfo('{"Dimmer": 70}', "home/bedroom/dimmer/status")
        dimmer.reportCmd.reset_mock()

        # User sends DOF command via ISY
        dimmer.off_cmd({"cmd": "DOF"})

        # Verify MQTT publish
        dimmer.controller.mqtt_pub.assert_called_with("home/bedroom/dimmer/cmd", OFF)
        assert dimmer.dimmer == OFF

        # MQTT broker echoes back the state
        dimmer.updateInfo('{"POWER": "OFF"}', "home/bedroom/dimmer/status")

        # State should remain OFF
        assert dimmer.dimmer == OFF

    def test_brightness_adjustment_workflow(self, full_dimmer_setup):
        """Test brightness adjustment while on."""
        dimmer = full_dimmer_setup

        # Start at 50%
        dimmer.on_cmd({"value": 50})
        assert dimmer.dimmer == 50

        # Brighten
        dimmer.brt_cmd({})
        assert dimmer.dimmer == 60

        # Brighten again
        dimmer.brt_cmd({})
        assert dimmer.dimmer == 70

        # Dim
        dimmer.dim_cmd({})
        assert dimmer.dimmer == 60

    def test_query_workflow(self, full_dimmer_setup):
        """Test query workflow."""
        dimmer = full_dimmer_setup

        # Query current state
        dimmer.query(None)

        # Should request update via State topic
        dimmer.controller.mqtt_pub.assert_called_with("home/bedroom/dimmer/State", "")
        dimmer.reportDrivers.assert_called_once()

    def test_external_state_change(self, full_dimmer_setup):
        """Test handling external state change (not from ISY)."""
        dimmer = full_dimmer_setup

        # External device (e.g., physical switch) turns on the dimmer
        dimmer.updateInfo('{"POWER": "ON", "Dimmer": 65}', "home/bedroom/dimmer/status")

        # Should update ISY to reflect new state
        assert dimmer.dimmer == 65
        dimmer.setDriver.assert_called_with("ST", 65)
        dimmer.reportCmd.assert_called_with("DON")

    def test_gradual_dimming_workflow(self, full_dimmer_setup):
        """Test gradual dimming via multiple DIM commands."""
        dimmer = full_dimmer_setup
        dimmer.on_cmd({"value": 100})

        # Dim gradually
        for expected in [90, 80, 70, 60, 50]:
            dimmer.dim_cmd({})
            assert dimmer.dimmer == expected

    def test_error_recovery_workflow(self, full_dimmer_setup):
        """Test error recovery from invalid messages."""
        dimmer = full_dimmer_setup
        dimmer.on_cmd({"value": 50})

        # Receive invalid JSON
        dimmer.updateInfo("invalid json", "home/bedroom/dimmer/status")

        # State should remain unchanged
        assert dimmer.dimmer == 50

        # Valid update should still work
        dimmer.updateInfo('{"Dimmer": 75}', "home/bedroom/dimmer/status")
        assert dimmer.dimmer == 75

    def test_power_toggle_workflow(self, full_dimmer_setup):
        """Test power toggle workflow."""
        dimmer = full_dimmer_setup

        # Turn on to 60%
        dimmer.updateInfo('{"POWER": "ON", "Dimmer": 60}', "home/bedroom/dimmer/status")
        assert dimmer.dimmer == 60

        # Turn off
        dimmer.updateInfo('{"POWER": "OFF"}', "home/bedroom/dimmer/status")
        assert dimmer.dimmer == OFF

        # Turn back on (should default to FULL since was OFF)
        dimmer.updateInfo('{"POWER": "ON"}', "home/bedroom/dimmer/status")
        assert dimmer.dimmer == FULL
