"""
Comprehensive test suite for MQratgdo node.

Tests cover:
- Initialization
- MQTT message handling for multiple topics
  - availability
  - light (on/off)
  - door (open/opening/stopped/closing/closed)
  - motion (detected/clear)
  - lock (locked/unlocked)
  - obstruction (obstructed/clear)
- Command handlers (DON/DOF/OPEN/CLOSE/STOP/LOCK/UNLOCK/MCLEAR/QUERY)
- Topic routing and handler dispatch
- State tracking for all drivers
- Error handling
"""

import pytest
from unittest.mock import Mock
from nodes.MQratgdo import (
    MQratgdo,
    DOOR_STATE_OPEN,
    DOOR_STATE_OPENING,
    DOOR_STATE_STOPPED,
    DOOR_STATE_CLOSING,
    DOOR_STATE_CLOSED,
    DOOR_PAYLOAD_MAP,
)


class TestMQratgdoInitialization:
    """Tests for MQratgdo initialization."""

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
        return {"cmd_topic": "home/garage/ratgdo"}

    def test_initialization_basic(self, mock_polyglot, device_config):
        """Test basic MQratgdo initialization."""
        controller = Mock()
        mock_polyglot.getNode.return_value = controller

        ratgdo = MQratgdo(
            mock_polyglot, "controller", "garage_1", "Garage Door", device_config
        )

        assert ratgdo.id == "mqratgdo"
        assert ratgdo.address == "garage_1"
        assert ratgdo.name == "Garage Door"
        assert ratgdo.cmd_topic == "home/garage/ratgdo/command/"
        assert ratgdo.device == device_config
        assert ratgdo.lpfx == "garage_1:Garage Door"

    def test_initialization_appends_command_path(self, mock_polyglot, device_config):
        """Test that initialization appends /command/ to cmd_topic."""
        controller = Mock()
        mock_polyglot.getNode.return_value = controller

        ratgdo = MQratgdo(
            mock_polyglot, "controller", "garage_1", "Test", device_config
        )

        # Should append /command/ to the base topic
        assert ratgdo.cmd_topic.endswith("/command/")

    def test_initialization_gets_controller(self, mock_polyglot, device_config):
        """Test that initialization retrieves the controller."""
        controller = Mock()
        mock_polyglot.getNode.return_value = controller

        ratgdo = MQratgdo(
            mock_polyglot, "controller", "garage_1", "Test", device_config
        )

        mock_polyglot.getNode.assert_called_once_with("controller")
        assert ratgdo.controller == controller


class TestMQratgdoHandleAvailability:
    """Tests for _handle_availability method."""

    @pytest.fixture
    def ratgdo(self):
        """Create a MQratgdo instance for testing."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/ratgdo"}
        r = MQratgdo(poly, "controller", "ratgdo1", "Test", device)
        r.setDriver = Mock()

        return r

    def test_handle_availability_online(self, ratgdo):
        """Test handling online availability."""
        ratgdo._handle_availability("online")

        ratgdo.setDriver.assert_called_once_with("ST", 1)

    def test_handle_availability_offline(self, ratgdo):
        """Test handling offline availability."""
        ratgdo._handle_availability("offline")

        ratgdo.setDriver.assert_called_once_with("ST", 0)

    def test_handle_availability_unknown_value(self, ratgdo):
        """Test handling unknown availability value."""
        ratgdo._handle_availability("unknown")

        ratgdo.setDriver.assert_called_once_with("ST", 0)


class TestMQratgdoHandleLight:
    """Tests for _handle_light method."""

    @pytest.fixture
    def ratgdo(self):
        """Create a MQratgdo instance for testing."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/ratgdo"}
        r = MQratgdo(poly, "controller", "ratgdo1", "Test", device)
        r.setDriver = Mock()

        return r

    def test_handle_light_on(self, ratgdo):
        """Test handling light on."""
        ratgdo._handle_light("on")

        ratgdo.setDriver.assert_called_once_with("GV0", 1)

    def test_handle_light_off(self, ratgdo):
        """Test handling light off."""
        ratgdo._handle_light("off")

        ratgdo.setDriver.assert_called_once_with("GV0", 0)

    def test_handle_light_case_sensitive(self, ratgdo):
        """Test that light handler is case-sensitive."""
        ratgdo._handle_light("ON")

        # Should be off since it's not lowercase "on"
        ratgdo.setDriver.assert_called_once_with("GV0", 0)


class TestMQratgdoHandleDoor:
    """Tests for _handle_door method."""

    @pytest.fixture
    def ratgdo(self):
        """Create a MQratgdo instance for testing."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/ratgdo"}
        r = MQratgdo(poly, "controller", "ratgdo1", "Test", device)
        r.setDriver = Mock()

        return r

    def test_handle_door_open(self, ratgdo):
        """Test handling door open state."""
        ratgdo._handle_door("open")

        ratgdo.setDriver.assert_called_once_with("GV1", DOOR_STATE_OPEN)

    def test_handle_door_opening(self, ratgdo):
        """Test handling door opening state."""
        ratgdo._handle_door("opening")

        ratgdo.setDriver.assert_called_once_with("GV1", DOOR_STATE_OPENING)

    def test_handle_door_stopped(self, ratgdo):
        """Test handling door stopped state."""
        ratgdo._handle_door("stopped")

        ratgdo.setDriver.assert_called_once_with("GV1", DOOR_STATE_STOPPED)

    def test_handle_door_closing(self, ratgdo):
        """Test handling door closing state."""
        ratgdo._handle_door("closing")

        ratgdo.setDriver.assert_called_once_with("GV1", DOOR_STATE_CLOSING)

    def test_handle_door_closed(self, ratgdo):
        """Test handling door closed state."""
        ratgdo._handle_door("closed")

        ratgdo.setDriver.assert_called_once_with("GV1", DOOR_STATE_CLOSED)

    def test_handle_door_unknown_state(self, ratgdo):
        """Test handling unknown door state defaults to closed."""
        ratgdo._handle_door("unknown")

        ratgdo.setDriver.assert_called_once_with("GV1", DOOR_STATE_CLOSED)


class TestMQratgdoHandleMotion:
    """Tests for _handle_motion method."""

    @pytest.fixture
    def ratgdo(self):
        """Create a MQratgdo instance for testing."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/ratgdo"}
        r = MQratgdo(poly, "controller", "ratgdo1", "Test", device)
        r.setDriver = Mock()

        return r

    def test_handle_motion_detected(self, ratgdo):
        """Test handling motion detected."""
        ratgdo._handle_motion("detected")

        ratgdo.setDriver.assert_called_once_with("GV2", 1)

    def test_handle_motion_clear(self, ratgdo):
        """Test handling motion clear."""
        ratgdo._handle_motion("clear")

        ratgdo.setDriver.assert_called_once_with("GV2", 0)

    def test_handle_motion_other_value(self, ratgdo):
        """Test handling other motion value."""
        ratgdo._handle_motion("unknown")

        ratgdo.setDriver.assert_called_once_with("GV2", 0)


class TestMQratgdoHandleLock:
    """Tests for _handle_lock method."""

    @pytest.fixture
    def ratgdo(self):
        """Create a MQratgdo instance for testing."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/ratgdo"}
        r = MQratgdo(poly, "controller", "ratgdo1", "Test", device)
        r.setDriver = Mock()

        return r

    def test_handle_lock_locked(self, ratgdo):
        """Test handling lock locked."""
        ratgdo._handle_lock("locked")

        ratgdo.setDriver.assert_called_once_with("GV3", 1)

    def test_handle_lock_unlocked(self, ratgdo):
        """Test handling lock unlocked."""
        ratgdo._handle_lock("unlocked")

        ratgdo.setDriver.assert_called_once_with("GV3", 0)

    def test_handle_lock_other_value(self, ratgdo):
        """Test handling other lock value."""
        ratgdo._handle_lock("unknown")

        ratgdo.setDriver.assert_called_once_with("GV3", 0)


class TestMQratgdoHandleObstruction:
    """Tests for _handle_obstruction method."""

    @pytest.fixture
    def ratgdo(self):
        """Create a MQratgdo instance for testing."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/ratgdo"}
        r = MQratgdo(poly, "controller", "ratgdo1", "Test", device)
        r.setDriver = Mock()

        return r

    def test_handle_obstruction_obstructed(self, ratgdo):
        """Test handling obstruction detected."""
        ratgdo._handle_obstruction("obstructed")

        ratgdo.setDriver.assert_called_once_with("GV4", 1)

    def test_handle_obstruction_clear(self, ratgdo):
        """Test handling obstruction clear."""
        ratgdo._handle_obstruction("clear")

        ratgdo.setDriver.assert_called_once_with("GV4", 0)

    def test_handle_obstruction_other_value(self, ratgdo):
        """Test handling other obstruction value."""
        ratgdo._handle_obstruction("unknown")

        ratgdo.setDriver.assert_called_once_with("GV4", 0)


class TestMQratgdoUpdateInfo:
    """Tests for updateInfo method (topic routing)."""

    @pytest.fixture
    def ratgdo(self):
        """Create a MQratgdo instance for testing."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/ratgdo"}
        r = MQratgdo(poly, "controller", "ratgdo1", "Test", device)
        r.setDriver = Mock()

        return r

    def test_update_info_availability_topic(self, ratgdo):
        """Test routing availability topic."""
        ratgdo.updateInfo("online", "test/ratgdo/status/availability")

        ratgdo.setDriver.assert_called_once_with("ST", 1)

    def test_update_info_light_topic(self, ratgdo):
        """Test routing light topic."""
        ratgdo.updateInfo("on", "test/ratgdo/status/light")

        ratgdo.setDriver.assert_called_once_with("GV0", 1)

    def test_update_info_door_topic(self, ratgdo):
        """Test routing door topic."""
        ratgdo.updateInfo("open", "test/ratgdo/status/door")

        ratgdo.setDriver.assert_called_once_with("GV1", DOOR_STATE_OPEN)

    def test_update_info_motion_topic(self, ratgdo):
        """Test routing motion topic."""
        ratgdo.updateInfo("detected", "test/ratgdo/status/motion")

        ratgdo.setDriver.assert_called_once_with("GV2", 1)

    def test_update_info_lock_topic(self, ratgdo):
        """Test routing lock topic."""
        ratgdo.updateInfo("locked", "test/ratgdo/status/lock")

        ratgdo.setDriver.assert_called_once_with("GV3", 1)

    def test_update_info_obstruction_topic(self, ratgdo):
        """Test routing obstruction topic."""
        ratgdo.updateInfo("obstructed", "test/ratgdo/status/obstruction")

        ratgdo.setDriver.assert_called_once_with("GV4", 1)

    def test_update_info_unknown_topic(self, ratgdo):
        """Test handling unknown topic suffix."""
        ratgdo.updateInfo("value", "test/ratgdo/status/unknown")

        # Should not call setDriver for unknown topic
        ratgdo.setDriver.assert_not_called()


class TestMQratgdoLightCommands:
    """Tests for light command handlers."""

    @pytest.fixture
    def ratgdo_with_controller(self):
        """Create a MQratgdo with mocked controller."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/ratgdo"}
        r = MQratgdo(poly, "controller", "ratgdo1", "Test", device)

        return r

    def test_lt_on(self, ratgdo_with_controller):
        """Test DON command turns light on."""
        command = {"cmd": "DON"}

        ratgdo_with_controller.lt_on(command)

        ratgdo_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/ratgdo/command/light", "on"
        )

    def test_lt_off(self, ratgdo_with_controller):
        """Test DOF command turns light off."""
        command = {"cmd": "DOF"}

        ratgdo_with_controller.lt_off(command)

        ratgdo_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/ratgdo/command/light", "off"
        )


class TestMQratgdoDoorCommands:
    """Tests for door command handlers."""

    @pytest.fixture
    def ratgdo_with_controller(self):
        """Create a MQratgdo with mocked controller."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/ratgdo"}
        r = MQratgdo(poly, "controller", "ratgdo1", "Test", device)

        return r

    def test_dr_open(self, ratgdo_with_controller):
        """Test OPEN command opens door."""
        command = {"cmd": "OPEN"}

        ratgdo_with_controller.dr_open(command)

        ratgdo_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/ratgdo/command/door", "open"
        )

    def test_dr_close(self, ratgdo_with_controller):
        """Test CLOSE command closes door."""
        command = {"cmd": "CLOSE"}

        ratgdo_with_controller.dr_close(command)

        ratgdo_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/ratgdo/command/door", "close"
        )

    def test_dr_stop(self, ratgdo_with_controller):
        """Test STOP command stops door."""
        command = {"cmd": "STOP"}

        ratgdo_with_controller.dr_stop(command)

        ratgdo_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/ratgdo/command/door", "stop"
        )


class TestMQratgdoLockCommands:
    """Tests for lock command handlers."""

    @pytest.fixture
    def ratgdo_with_controller(self):
        """Create a MQratgdo with mocked controller."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/ratgdo"}
        r = MQratgdo(poly, "controller", "ratgdo1", "Test", device)

        return r

    def test_lk_lock(self, ratgdo_with_controller):
        """Test LOCK command locks door."""
        command = {"cmd": "LOCK"}

        ratgdo_with_controller.lk_lock(command)

        ratgdo_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/ratgdo/command/lock", "lock"
        )

    def test_lk_unlock(self, ratgdo_with_controller):
        """Test UNLOCK command unlocks door."""
        command = {"cmd": "UNLOCK"}

        ratgdo_with_controller.lk_unlock(command)

        ratgdo_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/ratgdo/command/lock", "unlock"
        )


class TestMQratgdoMotionClear:
    """Tests for motion clear command handler."""

    @pytest.fixture
    def ratgdo_with_controller(self):
        """Create a MQratgdo with mocked controller."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/ratgdo"}
        r = MQratgdo(poly, "controller", "ratgdo1", "Test", device)
        r.setDriver = Mock()

        return r

    def test_m_clear(self, ratgdo_with_controller):
        """Test MCLEAR command clears motion."""
        command = {"cmd": "MCLEAR"}

        ratgdo_with_controller.m_clear(command)

        # Should publish to status topic (not command)
        ratgdo_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/ratgdo/status/motion", "Clear"
        )
        # Should also set driver to 0
        ratgdo_with_controller.setDriver.assert_called_once_with("GV2", 0)

    def test_m_clear_without_command(self, ratgdo_with_controller):
        """Test MCLEAR with None command."""
        ratgdo_with_controller.m_clear(None)

        ratgdo_with_controller.controller.mqtt_pub.assert_called_once()
        ratgdo_with_controller.setDriver.assert_called_once_with("GV2", 0)


class TestMQratgdoQuery:
    """Tests for query command handler."""

    @pytest.fixture
    def ratgdo_with_controller(self):
        """Create a MQratgdo with mocked controller."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/ratgdo"}
        r = MQratgdo(poly, "controller", "ratgdo1", "Test", device)
        r.reportDrivers = Mock()

        return r

    def test_query_command(self, ratgdo_with_controller):
        """Test QUERY command handler."""
        command = {"cmd": "QUERY"}

        ratgdo_with_controller.query(command)

        ratgdo_with_controller.reportDrivers.assert_called_once()

    def test_query_without_command(self, ratgdo_with_controller):
        """Test QUERY with None command."""
        ratgdo_with_controller.query(None)

        ratgdo_with_controller.reportDrivers.assert_called_once()


class TestMQratgdoDriversAndCommands:
    """Tests for node configuration (drivers, commands, etc.)."""

    def test_node_id(self):
        """Test that node ID is correct."""
        assert MQratgdo.id == "mqratgdo"

    def test_drivers_configuration(self):
        """Test drivers are properly configured."""
        assert hasattr(MQratgdo, "drivers")
        assert len(MQratgdo.drivers) == 6

        expected_drivers = {
            "ST": {"value": 0, "uom": 2, "name": "Status"},
            "GV0": {"value": 0, "uom": 2, "name": "Light"},
            "GV1": {"value": 0, "uom": 25, "name": "Door"},
            "GV2": {"value": 0, "uom": 2, "name": "Motion"},
            "GV3": {"value": 0, "uom": 2, "name": "Lock"},
            "GV4": {"value": 0, "uom": 2, "name": "Obstruction"},
        }

        for driver in MQratgdo.drivers:
            driver_code = driver["driver"]
            assert driver_code in expected_drivers
            expected = expected_drivers[driver_code]
            assert driver["value"] == expected["value"]
            assert driver["uom"] == expected["uom"]
            assert driver["name"] == expected["name"]

    def test_commands_configuration(self):
        """Test commands are properly configured."""
        assert hasattr(MQratgdo, "commands")
        assert "QUERY" in MQratgdo.commands
        assert "DON" in MQratgdo.commands
        assert "DOF" in MQratgdo.commands
        assert "OPEN" in MQratgdo.commands
        assert "CLOSE" in MQratgdo.commands
        assert "STOP" in MQratgdo.commands
        assert "LOCK" in MQratgdo.commands
        assert "UNLOCK" in MQratgdo.commands
        assert "MCLEAR" in MQratgdo.commands

        assert MQratgdo.commands["QUERY"] == MQratgdo.query
        assert MQratgdo.commands["DON"] == MQratgdo.lt_on
        assert MQratgdo.commands["DOF"] == MQratgdo.lt_off
        assert MQratgdo.commands["OPEN"] == MQratgdo.dr_open
        assert MQratgdo.commands["CLOSE"] == MQratgdo.dr_close
        assert MQratgdo.commands["STOP"] == MQratgdo.dr_stop
        assert MQratgdo.commands["LOCK"] == MQratgdo.lk_lock
        assert MQratgdo.commands["UNLOCK"] == MQratgdo.lk_unlock
        assert MQratgdo.commands["MCLEAR"] == MQratgdo.m_clear


class TestMQratgdoConstants:
    """Tests for module constants."""

    def test_door_state_constants(self):
        """Test door state constants."""
        assert DOOR_STATE_CLOSED == 0
        assert DOOR_STATE_OPEN == 1
        assert DOOR_STATE_OPENING == 2
        assert DOOR_STATE_STOPPED == 3
        assert DOOR_STATE_CLOSING == 4

    def test_door_payload_map(self):
        """Test door payload mapping."""
        assert DOOR_PAYLOAD_MAP["closed"] == DOOR_STATE_CLOSED
        assert DOOR_PAYLOAD_MAP["open"] == DOOR_STATE_OPEN
        assert DOOR_PAYLOAD_MAP["opening"] == DOOR_STATE_OPENING
        assert DOOR_PAYLOAD_MAP["stopped"] == DOOR_STATE_STOPPED
        assert DOOR_PAYLOAD_MAP["closing"] == DOOR_STATE_CLOSING

    def test_door_states_are_unique(self):
        """Test that all door states have unique values."""
        states = [
            DOOR_STATE_CLOSED,
            DOOR_STATE_OPEN,
            DOOR_STATE_OPENING,
            DOOR_STATE_STOPPED,
            DOOR_STATE_CLOSING,
        ]
        assert len(states) == len(set(states))


class TestMQratgdoIntegration:
    """Integration tests for complete workflows."""

    @pytest.fixture
    def full_ratgdo_setup(self):
        """Create a fully mocked Ratgdo setup."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "home/garage/ratgdo"}
        r = MQratgdo(poly, "controller", "ratgdo1", "Main Garage", device)
        r.setDriver = Mock()
        r.reportDrivers = Mock()

        return r

    def test_door_open_workflow(self, full_ratgdo_setup):
        """Test complete door open workflow."""
        ratgdo = full_ratgdo_setup

        # User sends OPEN command via ISY
        ratgdo.dr_open({"cmd": "OPEN"})

        # Verify MQTT publish
        ratgdo.controller.mqtt_pub.assert_called_with(
            "home/garage/ratgdo/command/door", "open"
        )

        # Device reports opening
        ratgdo.updateInfo("opening", "home/garage/ratgdo/status/door")
        ratgdo.setDriver.assert_called_with("GV1", DOOR_STATE_OPENING)

        ratgdo.setDriver.reset_mock()

        # Device reports fully open
        ratgdo.updateInfo("open", "home/garage/ratgdo/status/door")
        ratgdo.setDriver.assert_called_with("GV1", DOOR_STATE_OPEN)

    def test_door_close_workflow(self, full_ratgdo_setup):
        """Test complete door close workflow."""
        ratgdo = full_ratgdo_setup

        # User sends CLOSE command via ISY
        ratgdo.dr_close({"cmd": "CLOSE"})

        # Verify MQTT publish
        ratgdo.controller.mqtt_pub.assert_called_with(
            "home/garage/ratgdo/command/door", "close"
        )

        # Device reports closing
        ratgdo.updateInfo("closing", "home/garage/ratgdo/status/door")
        ratgdo.setDriver.assert_called_with("GV1", DOOR_STATE_CLOSING)

        ratgdo.setDriver.reset_mock()

        # Device reports fully closed
        ratgdo.updateInfo("closed", "home/garage/ratgdo/status/door")
        ratgdo.setDriver.assert_called_with("GV1", DOOR_STATE_CLOSED)

    def test_door_stop_workflow(self, full_ratgdo_setup):
        """Test door stop workflow."""
        ratgdo = full_ratgdo_setup

        # Door is opening
        ratgdo.updateInfo("opening", "home/garage/ratgdo/status/door")

        # User sends STOP command
        ratgdo.dr_stop({"cmd": "STOP"})
        ratgdo.controller.mqtt_pub.assert_called_with(
            "home/garage/ratgdo/command/door", "stop"
        )

        # Device reports stopped
        ratgdo.updateInfo("stopped", "home/garage/ratgdo/status/door")
        ratgdo.setDriver.assert_called_with("GV1", DOOR_STATE_STOPPED)

    def test_light_control_workflow(self, full_ratgdo_setup):
        """Test light control workflow."""
        ratgdo = full_ratgdo_setup

        # Turn light on
        ratgdo.lt_on({"cmd": "DON"})
        ratgdo.controller.mqtt_pub.assert_called_with(
            "home/garage/ratgdo/command/light", "on"
        )

        ratgdo.updateInfo("on", "home/garage/ratgdo/status/light")
        ratgdo.setDriver.assert_called_with("GV0", 1)

        ratgdo.setDriver.reset_mock()

        # Turn light off
        ratgdo.lt_off({"cmd": "DOF"})
        ratgdo.controller.mqtt_pub.assert_called_with(
            "home/garage/ratgdo/command/light", "off"
        )

        ratgdo.updateInfo("off", "home/garage/ratgdo/status/light")
        ratgdo.setDriver.assert_called_with("GV0", 0)

    def test_lock_control_workflow(self, full_ratgdo_setup):
        """Test lock control workflow."""
        ratgdo = full_ratgdo_setup

        # Lock door
        ratgdo.lk_lock({"cmd": "LOCK"})
        ratgdo.controller.mqtt_pub.assert_called_with(
            "home/garage/ratgdo/command/lock", "lock"
        )

        ratgdo.updateInfo("locked", "home/garage/ratgdo/status/lock")
        ratgdo.setDriver.assert_called_with("GV3", 1)

        ratgdo.setDriver.reset_mock()

        # Unlock door
        ratgdo.lk_unlock({"cmd": "UNLOCK"})
        ratgdo.controller.mqtt_pub.assert_called_with(
            "home/garage/ratgdo/command/lock", "unlock"
        )

        ratgdo.updateInfo("unlocked", "home/garage/ratgdo/status/lock")
        ratgdo.setDriver.assert_called_with("GV3", 0)

    def test_motion_detection_workflow(self, full_ratgdo_setup):
        """Test motion detection workflow."""
        ratgdo = full_ratgdo_setup

        # Motion detected
        ratgdo.updateInfo("detected", "home/garage/ratgdo/status/motion")
        ratgdo.setDriver.assert_called_with("GV2", 1)

        ratgdo.setDriver.reset_mock()

        # Clear motion
        ratgdo.m_clear({"cmd": "MCLEAR"})
        ratgdo.setDriver.assert_called_with("GV2", 0)

    def test_obstruction_detection_workflow(self, full_ratgdo_setup):
        """Test obstruction detection workflow."""
        ratgdo = full_ratgdo_setup

        # Obstruction detected
        ratgdo.updateInfo("obstructed", "home/garage/ratgdo/status/obstruction")
        ratgdo.setDriver.assert_called_with("GV4", 1)

        ratgdo.setDriver.reset_mock()

        # Obstruction cleared
        ratgdo.updateInfo("clear", "home/garage/ratgdo/status/obstruction")
        ratgdo.setDriver.assert_called_with("GV4", 0)

    def test_availability_workflow(self, full_ratgdo_setup):
        """Test device availability workflow."""
        ratgdo = full_ratgdo_setup

        # Device comes online
        ratgdo.updateInfo("online", "home/garage/ratgdo/status/availability")
        ratgdo.setDriver.assert_called_with("ST", 1)

        ratgdo.setDriver.reset_mock()

        # Device goes offline
        ratgdo.updateInfo("offline", "home/garage/ratgdo/status/availability")
        ratgdo.setDriver.assert_called_with("ST", 0)

    def test_query_workflow(self, full_ratgdo_setup):
        """Test query workflow."""
        ratgdo = full_ratgdo_setup

        # Query current state
        ratgdo.query(None)

        ratgdo.reportDrivers.assert_called_once()

    def test_complete_garage_scenario(self, full_ratgdo_setup):
        """Test complete garage usage scenario."""
        ratgdo = full_ratgdo_setup

        # Device comes online
        ratgdo.updateInfo("online", "home/garage/ratgdo/status/availability")

        # Motion detected (car approaching)
        ratgdo.updateInfo("detected", "home/garage/ratgdo/status/motion")

        # Turn on light
        ratgdo.lt_on({"cmd": "DON"})
        ratgdo.updateInfo("on", "home/garage/ratgdo/status/light")

        # Open door
        ratgdo.dr_open({"cmd": "OPEN"})
        ratgdo.updateInfo("opening", "home/garage/ratgdo/status/door")
        ratgdo.updateInfo("open", "home/garage/ratgdo/status/door")

        # Close door
        ratgdo.dr_close({"cmd": "CLOSE"})
        ratgdo.updateInfo("closing", "home/garage/ratgdo/status/door")
        ratgdo.updateInfo("closed", "home/garage/ratgdo/status/door")

        # Turn off light
        ratgdo.lt_off({"cmd": "DOF"})
        ratgdo.updateInfo("off", "home/garage/ratgdo/status/light")

        # Lock door
        ratgdo.lk_lock({"cmd": "LOCK"})
        ratgdo.updateInfo("locked", "home/garage/ratgdo/status/lock")

        # All commands should have been published
        assert ratgdo.controller.mqtt_pub.call_count >= 4
