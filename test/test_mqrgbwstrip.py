"""
Comprehensive test suite for MQRGBWstrip node.

Tests cover:
- Initialization
- MQTT message handling (JSON payloads with LED state and colors)
- State tracking (ON/OFF)
- RGBW color control
- Brightness control
- Program control
- Command handlers (DON/DOF/SETRGBW/QUERY)
- Value clamping (0-255)
- Error handling
"""

import pytest
from unittest.mock import Mock
import json
from nodes.MQRGBWstrip import MQRGBWstrip, LED_ON_VALUE, LED_OFF_VALUE, COLOR_MAX_VALUE


class TestMQRGBWstripInitialization:
    """Tests for MQRGBWstrip initialization."""

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
        return {"cmd_topic": "home/led/1/cmd"}

    def test_initialization_basic(self, mock_polyglot, device_config):
        """Test basic MQRGBWstrip initialization."""
        controller = Mock()
        mock_polyglot.getNode.return_value = controller

        strip = MQRGBWstrip(
            mock_polyglot, "controller", "led_1", "Living Room LED", device_config
        )

        assert strip.id == "mqrgbw"
        assert strip.address == "led_1"
        assert strip.name == "Living Room LED"
        assert strip.cmd_topic == "home/led/1/cmd"
        assert strip.lpfx == "led_1:Living Room LED"

    def test_initialization_gets_controller(self, mock_polyglot, device_config):
        """Test that initialization retrieves the controller."""
        controller = Mock()
        mock_polyglot.getNode.return_value = controller

        strip = MQRGBWstrip(
            mock_polyglot, "controller", "led_1", "Test LED", device_config
        )

        mock_polyglot.getNode.assert_called_once_with("controller")
        assert strip.controller == controller

    def test_initialization_with_different_topic(self, mock_polyglot):
        """Test initialization with different MQTT topic."""
        device = {"cmd_topic": "custom/led/topic"}
        controller = Mock()
        mock_polyglot.getNode.return_value = controller

        strip = MQRGBWstrip(mock_polyglot, "controller", "led_2", "LED", device)

        assert strip.cmd_topic == "custom/led/topic"


class TestMQRGBWstripUpdateInfo:
    """Tests for updateInfo method (MQTT message handling)."""

    @pytest.fixture
    def strip(self):
        """Create a MQRGBWstrip instance for testing."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/led/cmd"}
        s = MQRGBWstrip(poly, "controller", "led1", "Test", device)
        s.setDriver = Mock()
        s.reportCmd = Mock()

        return s

    def test_update_info_state_on(self, strip):
        """Test receiving state ON."""
        payload = '{"state": "ON"}'
        strip.updateInfo(payload, "test/led/state")

        strip.setDriver.assert_called_once_with("GV0", LED_ON_VALUE)
        strip.reportCmd.assert_called_once_with("DON")

    def test_update_info_state_off(self, strip):
        """Test receiving state OFF."""
        payload = '{"state": "OFF"}'
        strip.updateInfo(payload, "test/led/state")

        strip.setDriver.assert_called_once_with("GV0", LED_OFF_VALUE)
        strip.reportCmd.assert_called_once_with("DOF")

    def test_update_info_brightness(self, strip):
        """Test receiving brightness value."""
        payload = '{"br": 128}'
        strip.updateInfo(payload, "test/led/state")

        strip.setDriver.assert_called_once_with("GV1", 128)

    def test_update_info_complete_rgbw(self, strip):
        """Test receiving complete RGBW color data."""
        payload = '{"c": {"r": 255, "g": 128, "b": 64, "w": 32}}'
        strip.updateInfo(payload, "test/led/state")

        strip.setDriver.assert_any_call("GV2", 255)
        strip.setDriver.assert_any_call("GV3", 128)
        strip.setDriver.assert_any_call("GV4", 64)
        strip.setDriver.assert_any_call("GV5", 32)

    def test_update_info_program(self, strip):
        """Test receiving program value."""
        payload = '{"pgm": 5}'
        strip.updateInfo(payload, "test/led/state")

        strip.setDriver.assert_called_once_with("GV6", 5)

    def test_update_info_full_payload(self, strip):
        """Test receiving complete payload with all fields."""
        payload = """{
            "state": "ON",
            "br": 200,
            "c": {"r": 255, "g": 100, "b": 50, "w": 0},
            "pgm": 3
        }"""
        strip.updateInfo(payload, "test/led/state")

        # Check all drivers were set
        strip.setDriver.assert_any_call("GV0", LED_ON_VALUE)
        strip.setDriver.assert_any_call("GV1", 200)
        strip.setDriver.assert_any_call("GV2", 255)
        strip.setDriver.assert_any_call("GV3", 100)
        strip.setDriver.assert_any_call("GV4", 50)
        strip.setDriver.assert_any_call("GV5", 0)
        strip.setDriver.assert_any_call("GV6", 3)
        strip.reportCmd.assert_called_once_with("DON")

    def test_update_info_partial_color_data(self, strip):
        """Test receiving partial color data."""
        payload = '{"c": {"r": 255, "g": 128}}'
        strip.updateInfo(payload, "test/led/state")

        strip.setDriver.assert_any_call("GV2", 255)
        strip.setDriver.assert_any_call("GV3", 128)
        strip.setDriver.assert_any_call("GV4", None)
        strip.setDriver.assert_any_call("GV5", None)

    def test_update_info_color_not_dict(self, strip):
        """Test handling color data that is not a dict."""
        payload = '{"c": "invalid"}'
        strip.updateInfo(payload, "test/led/state")

        # Should not call setDriver for color values
        strip.setDriver.assert_not_called()

    def test_update_info_invalid_json(self, strip):
        """Test handling invalid JSON payload."""
        payload = "not valid json{"
        strip.updateInfo(payload, "test/led/state")

        # Should not call setDriver
        strip.setDriver.assert_not_called()
        strip.reportCmd.assert_not_called()

    def test_update_info_empty_payload(self, strip):
        """Test handling empty JSON object."""
        payload = "{}"
        strip.updateInfo(payload, "test/led/state")

        # Should not crash, just do nothing
        strip.setDriver.assert_not_called()

    def test_update_info_state_case_sensitive(self, strip):
        """Test that state must be exactly 'ON' (case-sensitive)."""
        payload = '{"state": "on"}'
        strip.updateInfo(payload, "test/led/state")

        # Should set to OFF since it's not "ON"
        strip.setDriver.assert_called_once_with("GV0", LED_OFF_VALUE)
        strip.reportCmd.assert_called_once_with("DOF")

    def test_update_info_zero_brightness(self, strip):
        """Test receiving zero brightness."""
        payload = '{"br": 0}'
        strip.updateInfo(payload, "test/led/state")

        strip.setDriver.assert_called_once_with("GV1", 0)

    def test_update_info_max_brightness(self, strip):
        """Test receiving maximum brightness."""
        payload = '{"br": 255}'
        strip.updateInfo(payload, "test/led/state")

        strip.setDriver.assert_called_once_with("GV1", 255)


class TestMQRGBWstripCheckLimit:
    """Tests for _check_limit method (value clamping)."""

    @pytest.fixture
    def strip(self):
        """Create a MQRGBWstrip instance for testing."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/led/cmd"}
        s = MQRGBWstrip(poly, "controller", "led1", "Test", device)

        return s

    def test_check_limit_valid_value(self, strip):
        """Test clamping with valid value."""
        assert strip._check_limit(128) == 128

    def test_check_limit_zero(self, strip):
        """Test clamping zero."""
        assert strip._check_limit(0) == 0

    def test_check_limit_max(self, strip):
        """Test clamping maximum value."""
        assert strip._check_limit(255) == 255

    def test_check_limit_exceeds_max(self, strip):
        """Test clamping value above maximum."""
        assert strip._check_limit(300) == 255

    def test_check_limit_negative(self, strip):
        """Test clamping negative value."""
        assert strip._check_limit(-10) == 0

    def test_check_limit_large_negative(self, strip):
        """Test clamping large negative value."""
        assert strip._check_limit(-1000) == 0


class TestMQRGBWstripLedOn:
    """Tests for led_on command handler."""

    @pytest.fixture
    def strip_with_controller(self):
        """Create a MQRGBWstrip with mocked controller."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/led/cmd"}
        s = MQRGBWstrip(poly, "controller", "led1", "Test", device)

        return s

    def test_led_on(self, strip_with_controller):
        """Test DON command turns LED on."""
        command = {"cmd": "DON"}

        strip_with_controller.led_on(command)

        # Should publish state: ON
        strip_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/led/cmd", json.dumps({"state": "ON"})
        )


class TestMQRGBWstripLedOff:
    """Tests for led_off command handler."""

    @pytest.fixture
    def strip_with_controller(self):
        """Create a MQRGBWstrip with mocked controller."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/led/cmd"}
        s = MQRGBWstrip(poly, "controller", "led1", "Test", device)

        return s

    def test_led_off(self, strip_with_controller):
        """Test DOF command turns LED off."""
        command = {"cmd": "DOF"}

        strip_with_controller.led_off(command)

        # Should publish state: OFF
        strip_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/led/cmd", json.dumps({"state": "OFF"})
        )


class TestMQRGBWstripRgbwSet:
    """Tests for rgbw_set command handler."""

    @pytest.fixture
    def strip_with_controller(self):
        """Create a MQRGBWstrip with mocked controller."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/led/cmd"}
        s = MQRGBWstrip(poly, "controller", "led1", "Test", device)

        return s

    def test_rgbw_set_all_values(self, strip_with_controller):
        """Test SETRGBW command with all values."""
        command = {
            "query": {
                "STRIPR.uom100": "255",
                "STRIPG.uom100": "128",
                "STRIPB.uom100": "64",
                "STRIPW.uom100": "32",
                "STRIPI.uom100": "200",
                "STRIPP.uom100": "3",
            }
        }

        strip_with_controller.rgbw_set(command)

        # Check the published payload
        expected_cmd = {
            "state": "ON",
            "br": 200,
            "c": {"r": 255, "g": 128, "b": 64, "w": 32},
            "pgm": 3,
        }
        strip_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/led/cmd", json.dumps(expected_cmd)
        )

    def test_rgbw_set_with_defaults(self, strip_with_controller):
        """Test SETRGBW command with missing values (defaults to 0)."""
        command = {"query": {}}

        strip_with_controller.rgbw_set(command)

        # Should use 0 for all missing values
        expected_cmd = {
            "state": "ON",
            "br": 0,
            "c": {"r": 0, "g": 0, "b": 0, "w": 0},
            "pgm": 0,
        }
        strip_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/led/cmd", json.dumps(expected_cmd)
        )

    def test_rgbw_set_clamps_high_values(self, strip_with_controller):
        """Test SETRGBW command clamps values above 255."""
        command = {
            "query": {
                "STRIPR.uom100": "300",
                "STRIPG.uom100": "500",
                "STRIPB.uom100": "1000",
                "STRIPW.uom100": "256",
                "STRIPI.uom100": "300",
                "STRIPP.uom100": "300",
            }
        }

        strip_with_controller.rgbw_set(command)

        # All values should be clamped to 255
        expected_cmd = {
            "state": "ON",
            "br": 255,
            "c": {"r": 255, "g": 255, "b": 255, "w": 255},
            "pgm": 255,
        }
        strip_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/led/cmd", json.dumps(expected_cmd)
        )

    def test_rgbw_set_clamps_negative_values(self, strip_with_controller):
        """Test SETRGBW command clamps negative values to 0."""
        command = {
            "query": {
                "STRIPR.uom100": "-10",
                "STRIPG.uom100": "-50",
                "STRIPB.uom100": "-100",
                "STRIPW.uom100": "-5",
                "STRIPI.uom100": "-20",
                "STRIPP.uom100": "-30",
            }
        }

        strip_with_controller.rgbw_set(command)

        # All negative values should be clamped to 0
        expected_cmd = {
            "state": "ON",
            "br": 0,
            "c": {"r": 0, "g": 0, "b": 0, "w": 0},
            "pgm": 0,
        }
        strip_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/led/cmd", json.dumps(expected_cmd)
        )


class TestMQRGBWstripQuery:
    """Tests for query command handler."""

    @pytest.fixture
    def strip_with_controller(self):
        """Create a MQRGBWstrip with mocked controller."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/led/cmd"}
        s = MQRGBWstrip(poly, "controller", "led1", "Test", device)
        s.reportDrivers = Mock()

        return s

    def test_query_command(self, strip_with_controller):
        """Test QUERY command handler."""
        command = {"cmd": "QUERY"}

        strip_with_controller.query(command)

        strip_with_controller.reportDrivers.assert_called_once()

    def test_query_without_command(self, strip_with_controller):
        """Test QUERY with None command."""
        strip_with_controller.query(None)

        strip_with_controller.reportDrivers.assert_called_once()


class TestMQRGBWstripDriversAndCommands:
    """Tests for node configuration (drivers, commands, etc.)."""

    def test_node_id(self):
        """Test that node ID is correct."""
        assert MQRGBWstrip.id == "mqrgbw"

    def test_drivers_configuration(self):
        """Test drivers are properly configured."""
        assert hasattr(MQRGBWstrip, "drivers")
        assert len(MQRGBWstrip.drivers) == 8

        expected_drivers = {
            "ST": {"value": 0, "uom": 2, "name": "Status"},
            "GV0": {"value": 0, "uom": 78, "name": "State"},
            "GV1": {"value": 0, "uom": 100, "name": "Brightness"},
            "GV2": {"value": 0, "uom": 100, "name": "Red"},
            "GV3": {"value": 0, "uom": 100, "name": "Green"},
            "GV4": {"value": 0, "uom": 100, "name": "Blue"},
            "GV5": {"value": 0, "uom": 100, "name": "White"},
            "GV6": {"value": 0, "uom": 100, "name": "Program"},
        }

        for driver in MQRGBWstrip.drivers:
            driver_code = driver["driver"]
            assert driver_code in expected_drivers
            expected = expected_drivers[driver_code]
            assert driver["value"] == expected["value"]
            assert driver["uom"] == expected["uom"]
            assert driver["name"] == expected["name"]

    def test_commands_configuration(self):
        """Test commands are properly configured."""
        assert hasattr(MQRGBWstrip, "commands")
        assert "QUERY" in MQRGBWstrip.commands
        assert "DON" in MQRGBWstrip.commands
        assert "DOF" in MQRGBWstrip.commands
        assert "SETRGBW" in MQRGBWstrip.commands

        assert MQRGBWstrip.commands["QUERY"] == MQRGBWstrip.query
        assert MQRGBWstrip.commands["DON"] == MQRGBWstrip.led_on
        assert MQRGBWstrip.commands["DOF"] == MQRGBWstrip.led_off
        assert MQRGBWstrip.commands["SETRGBW"] == MQRGBWstrip.rgbw_set


class TestMQRGBWstripConstants:
    """Tests for module constants."""

    def test_led_on_value(self):
        """Test LED ON constant."""
        assert LED_ON_VALUE == 100

    def test_led_off_value(self):
        """Test LED OFF constant."""
        assert LED_OFF_VALUE == 0

    def test_color_max_value(self):
        """Test color max constant."""
        assert COLOR_MAX_VALUE == 255

    def test_values_are_distinct(self):
        """Test that ON and OFF values are different."""
        assert LED_ON_VALUE != LED_OFF_VALUE


class TestMQRGBWstripIntegration:
    """Integration tests for complete workflows."""

    @pytest.fixture
    def full_strip_setup(self):
        """Create a fully mocked LED strip setup."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "home/bedroom/led/cmd"}
        s = MQRGBWstrip(poly, "controller", "led1", "Bedroom LED", device)
        s.setDriver = Mock()
        s.reportCmd = Mock()
        s.reportDrivers = Mock()

        return s

    def test_full_on_workflow(self, full_strip_setup):
        """Test complete ON workflow: command -> MQTT -> update."""
        strip = full_strip_setup

        # User sends DON command via ISY
        strip.led_on({"cmd": "DON"})

        # Verify MQTT publish
        strip.controller.mqtt_pub.assert_called_with(
            "home/bedroom/led/cmd", json.dumps({"state": "ON"})
        )

        # MQTT broker echoes back the state
        strip.updateInfo('{"state": "ON"}', "home/bedroom/led/state")

        # Verify state updated
        strip.setDriver.assert_called_with("GV0", LED_ON_VALUE)
        strip.reportCmd.assert_called_with("DON")

    def test_full_off_workflow(self, full_strip_setup):
        """Test complete OFF workflow: command -> MQTT -> update."""
        strip = full_strip_setup

        # User sends DOF command via ISY
        strip.led_off({"cmd": "DOF"})

        # Verify MQTT publish
        strip.controller.mqtt_pub.assert_called_with(
            "home/bedroom/led/cmd", json.dumps({"state": "OFF"})
        )

        # MQTT broker echoes back the state
        strip.updateInfo('{"state": "OFF"}', "home/bedroom/led/state")

        # Verify state updated
        strip.setDriver.assert_called_with("GV0", LED_OFF_VALUE)
        strip.reportCmd.assert_called_with("DOF")

    def test_color_change_workflow(self, full_strip_setup):
        """Test color change workflow."""
        strip = full_strip_setup

        # Set to red
        command = {
            "query": {
                "STRIPR.uom100": "255",
                "STRIPG.uom100": "0",
                "STRIPB.uom100": "0",
                "STRIPW.uom100": "0",
                "STRIPI.uom100": "255",
                "STRIPP.uom100": "0",
            }
        }
        strip.rgbw_set(command)

        # Device echoes back
        strip.updateInfo(
            '{"state": "ON", "br": 255, "c": {"r": 255, "g": 0, "b": 0, "w": 0}, "pgm": 0}',
            "home/bedroom/led/state",
        )

        strip.setDriver.assert_any_call("GV2", 255)
        strip.setDriver.assert_any_call("GV3", 0)
        strip.setDriver.assert_any_call("GV4", 0)

    def test_query_workflow(self, full_strip_setup):
        """Test query workflow."""
        strip = full_strip_setup

        # Query current state
        strip.query(None)

        strip.reportDrivers.assert_called_once()

    def test_error_recovery_workflow(self, full_strip_setup):
        """Test error recovery from invalid messages."""
        strip = full_strip_setup

        # Receive valid data first
        strip.updateInfo('{"state": "ON", "br": 200}', "home/bedroom/led/state")
        strip.setDriver.reset_mock()

        # Receive invalid JSON
        strip.updateInfo("invalid json", "home/bedroom/led/state")
        strip.setDriver.assert_not_called()

        # Valid update should still work
        strip.updateInfo('{"state": "OFF"}', "home/bedroom/led/state")
        strip.setDriver.assert_called()

    def test_rgb_color_presets_workflow(self, full_strip_setup):
        """Test various RGB color preset scenarios."""
        strip = full_strip_setup

        # Pure red
        strip.updateInfo('{"c": {"r": 255, "g": 0, "b": 0, "w": 0}}', "state")
        strip.setDriver.assert_any_call("GV2", 255)

        strip.setDriver.reset_mock()

        # Pure green
        strip.updateInfo('{"c": {"r": 0, "g": 255, "b": 0, "w": 0}}', "state")
        strip.setDriver.assert_any_call("GV3", 255)

        strip.setDriver.reset_mock()

        # Pure blue
        strip.updateInfo('{"c": {"r": 0, "g": 0, "b": 255, "w": 0}}', "state")
        strip.setDriver.assert_any_call("GV4", 255)

        strip.setDriver.reset_mock()

        # White (all colors)
        strip.updateInfo('{"c": {"r": 255, "g": 255, "b": 255, "w": 255}}', "state")
        strip.setDriver.assert_any_call("GV2", 255)
        strip.setDriver.assert_any_call("GV3", 255)
        strip.setDriver.assert_any_call("GV4", 255)
        strip.setDriver.assert_any_call("GV5", 255)

    def test_brightness_adjustment_workflow(self, full_strip_setup):
        """Test brightness adjustment scenarios."""
        strip = full_strip_setup

        # Set to 50% brightness
        strip.updateInfo('{"br": 128}', "state")
        strip.setDriver.assert_called_with("GV1", 128)

        strip.setDriver.reset_mock()

        # Dim to 25%
        strip.updateInfo('{"br": 64}', "state")
        strip.setDriver.assert_called_with("GV1", 64)

        strip.setDriver.reset_mock()

        # Full brightness
        strip.updateInfo('{"br": 255}', "state")
        strip.setDriver.assert_called_with("GV1", 255)

    def test_program_selection_workflow(self, full_strip_setup):
        """Test program selection workflow."""
        strip = full_strip_setup

        # Select program 1
        strip.updateInfo('{"pgm": 1}', "state")
        strip.setDriver.assert_called_with("GV6", 1)

        strip.setDriver.reset_mock()

        # Select program 5
        strip.updateInfo('{"pgm": 5}', "state")
        strip.setDriver.assert_called_with("GV6", 5)
