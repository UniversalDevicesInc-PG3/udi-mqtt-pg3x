"""
Comprehensive test suite for MQSensor node.

Tests cover:
- Initialization
- JSON payload parsing
- Motion sensor updates
- Environmental sensors (temp, humidity, light)
- LED control (on/off/color/brightness)
- Command handling (DON, DOF, SETLED)
- Edge cases and error handling
"""

import json
import pytest
from unittest.mock import Mock
from nodes.MQSensor import MQSensor


class TestMQSensorInitialization:
    """Tests for MQSensor initialization."""

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
        return {"cmd_topic": "home/sensor/1/cmd"}

    def test_initialization_basic(self, mock_polyglot, device_config):
        """Test basic MQSensor initialization."""
        controller = Mock()
        mock_polyglot.getNode.return_value = controller

        sensor = MQSensor(
            mock_polyglot, "controller", "sens_1", "Multi Sensor", device_config
        )

        assert sensor.id == "mqsens"
        assert sensor.address == "sens_1"
        assert sensor.name == "Multi Sensor"
        assert sensor.cmd_topic == "home/sensor/1/cmd"
        assert sensor.lpfx == "sens_1:Multi Sensor"
        assert sensor.motion is False
        assert sensor.controller == controller

    def test_initialization_motion_state(self, mock_polyglot, device_config):
        """Test that motion starts as False."""
        mock_polyglot.getNode.return_value = Mock()

        sensor = MQSensor(mock_polyglot, "controller", "sens_1", "Test", device_config)

        assert sensor.motion is False


class TestMQSensorUpdateInfo:
    """Tests for updateInfo method (JSON message handling)."""

    @pytest.fixture
    def sensor(self):
        """Create a MQSensor instance for testing."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/sensor/cmd"}
        s = MQSensor(poly, "controller", "sens1", "Test", device)
        s.setDriver = Mock()
        s.reportCmd = Mock()

        return s

    def test_update_info_motion_active(self, sensor):
        """Test handling motion detected."""
        payload = json.dumps({"motion": "active"})

        sensor.updateInfo(payload, "test/sensor/state")

        sensor.setDriver.assert_called_with("ST", 1)
        sensor.reportCmd.assert_called_with("DON")
        assert sensor.motion is True

    def test_update_info_motion_standby(self, sensor):
        """Test handling motion standby."""
        # First set motion to True
        sensor.motion = True

        payload = json.dumps({"motion": "standby"})
        sensor.updateInfo(payload, "test/sensor/state")

        sensor.setDriver.assert_called_with("ST", 0)
        sensor.reportCmd.assert_called_with("DOF")
        assert sensor.motion is False

    def test_update_info_motion_standby_already_false(self, sensor):
        """Test motion standby when already in standby."""
        sensor.motion = False

        payload = json.dumps({"motion": "standby"})
        sensor.updateInfo(payload, "test/sensor/state")

        sensor.setDriver.assert_called_with("ST", 0)
        # Should not call reportCmd since motion was already False
        sensor.reportCmd.assert_not_called()

    def test_update_info_no_motion_field(self, sensor):
        """Test payload without motion field."""
        payload = json.dumps({"temperature": 72})

        sensor.updateInfo(payload, "test/sensor/state")

        # Should set ST to 0 when motion field is missing
        sensor.setDriver.assert_any_call("ST", 0)

    def test_update_info_temperature(self, sensor):
        """Test handling temperature update."""
        payload = json.dumps({"temperature": 72.5})

        sensor.updateInfo(payload, "test/sensor/state")

        sensor.setDriver.assert_any_call("CLITEMP", 72.5)

    def test_update_info_humidity(self, sensor):
        """Test handling humidity update."""
        payload = json.dumps({"humidity": 65})

        sensor.updateInfo(payload, "test/sensor/state")

        sensor.setDriver.assert_any_call("CLIHUM", 65)

    def test_update_info_heat_index(self, sensor):
        """Test handling heat index update."""
        payload = json.dumps({"heatIndex": 75.2})

        sensor.updateInfo(payload, "test/sensor/state")

        sensor.setDriver.assert_any_call("GPV", 75.2)

    def test_update_info_light_sensor(self, sensor):
        """Test handling light sensor (ldr) update."""
        payload = json.dumps({"ldr": 850})

        sensor.updateInfo(payload, "test/sensor/state")

        sensor.setDriver.assert_any_call("LUMIN", 850)

    def test_update_info_led_state_on(self, sensor):
        """Test handling LED state ON."""
        payload = json.dumps({"state": "ON"})

        sensor.updateInfo(payload, "test/sensor/state")

        sensor.setDriver.assert_any_call("GV0", 100)

    def test_update_info_led_state_off(self, sensor):
        """Test handling LED state OFF."""
        payload = json.dumps({"state": "OFF"})

        sensor.updateInfo(payload, "test/sensor/state")

        sensor.setDriver.assert_any_call("GV0", 0)

    def test_update_info_led_brightness(self, sensor):
        """Test handling LED brightness."""
        payload = json.dumps({"brightness": 128})

        sensor.updateInfo(payload, "test/sensor/state")

        sensor.setDriver.assert_any_call("GV1", 128)

    def test_update_info_led_color_rgb(self, sensor):
        """Test handling LED RGB color."""
        payload = json.dumps({"color": {"r": 255, "g": 100, "b": 50}})

        sensor.updateInfo(payload, "test/sensor/state")

        sensor.setDriver.assert_any_call("GV2", 255)
        sensor.setDriver.assert_any_call("GV3", 100)
        sensor.setDriver.assert_any_call("GV4", 50)

    def test_update_info_led_color_partial(self, sensor):
        """Test handling LED color with only some RGB values."""
        payload = json.dumps({"color": {"r": 200}})

        sensor.updateInfo(payload, "test/sensor/state")

        sensor.setDriver.assert_any_call("GV2", 200)
        # Should not call for g or b

    def test_update_info_complete_payload(self, sensor):
        """Test handling complete sensor payload."""
        payload = json.dumps({
            "motion": "active",
            "temperature": 72.0,
            "humidity": 55,
            "heatIndex": 73.5,
            "ldr": 750,
            "state": "ON",
            "brightness": 200,
            "color": {"r": 255, "g": 128, "b": 64}
        })

        sensor.updateInfo(payload, "test/sensor/state")

        # Verify all drivers were updated
        assert sensor.setDriver.call_count >= 10
        assert sensor.motion is True

    def test_update_info_invalid_json(self, sensor):
        """Test handling invalid JSON payload."""
        payload = "not valid json {"

        sensor.updateInfo(payload, "test/sensor/state")

        # Should not call setDriver due to JSON error
        sensor.setDriver.assert_not_called()

    def test_update_info_empty_json(self, sensor):
        """Test handling empty JSON object."""
        payload = json.dumps({})

        sensor.updateInfo(payload, "test/sensor/state")

        # Should set ST to 0 since motion field is missing
        sensor.setDriver.assert_called_with("ST", 0)

    def test_update_info_color_not_dict(self, sensor):
        """Test handling color field that is not a dict."""
        payload = json.dumps({"color": "red"})

        sensor.updateInfo(payload, "test/sensor/state")

        # Should not crash, just skip color processing
        # No assertions needed, just verify it doesn't raise


class TestMQSensorCommands:
    """Tests for command handlers."""

    @pytest.fixture
    def sensor_with_controller(self):
        """Create a MQSensor with mocked controller."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/sensor/cmd"}
        s = MQSensor(poly, "controller", "sens1", "Test", device)

        return s

    def test_led_on_command(self, sensor_with_controller):
        """Test LED ON command."""
        command = {"cmd": "DON"}

        sensor_with_controller.led_on(command)

        expected_payload = json.dumps({"state": "ON"})
        sensor_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/sensor/cmd", expected_payload
        )

    def test_led_off_command(self, sensor_with_controller):
        """Test LED OFF command."""
        command = {"cmd": "DOF"}

        sensor_with_controller.led_off(command)

        expected_payload = json.dumps({"state": "OFF"})
        sensor_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/sensor/cmd", expected_payload
        )

    def test_led_set_basic(self, sensor_with_controller):
        """Test SETLED command with basic parameters."""
        command = {
            "cmd": "SETLED",
            "query": {
                "R.uom100": "255",
                "G.uom100": "128",
                "B.uom100": "64",
                "I.uom100": "200",
            }
        }

        sensor_with_controller.led_set(command)

        # Verify MQTT message was sent
        assert sensor_with_controller.controller.mqtt_pub.called
        call_args = sensor_with_controller.controller.mqtt_pub.call_args
        sent_payload = json.loads(call_args[0][1])

        assert sent_payload["state"] == "ON"
        assert sent_payload["brightness"] == 200
        assert sent_payload["color"]["r"] == 255
        assert sent_payload["color"]["g"] == 128
        assert sent_payload["color"]["b"] == 64

    def test_led_set_with_transition(self, sensor_with_controller):
        """Test SETLED command with transition."""
        command = {
            "cmd": "SETLED",
            "query": {
                "R.uom100": "255",
                "G.uom100": "0",
                "B.uom100": "0",
                "I.uom100": "255",
                "D.uom58": "500",
            }
        }

        sensor_with_controller.led_set(command)

        call_args = sensor_with_controller.controller.mqtt_pub.call_args
        sent_payload = json.loads(call_args[0][1])

        assert sent_payload["transition"] == 500

    def test_led_set_with_flash(self, sensor_with_controller):
        """Test SETLED command with flash."""
        command = {
            "cmd": "SETLED",
            "query": {
                "R.uom100": "0",
                "G.uom100": "255",
                "B.uom100": "0",
                "I.uom100": "255",
                "F.uom58": "3",
            }
        }

        sensor_with_controller.led_set(command)

        call_args = sensor_with_controller.controller.mqtt_pub.call_args
        sent_payload = json.loads(call_args[0][1])

        assert sent_payload["flash"] == 3

    def test_led_set_no_transition_or_flash(self, sensor_with_controller):
        """Test SETLED without optional transition/flash parameters."""
        command = {
            "cmd": "SETLED",
            "query": {
                "R.uom100": "100",
                "G.uom100": "100",
                "B.uom100": "100",
                "I.uom100": "100",
                "D.uom58": "0",
                "F.uom58": "0",
            }
        }

        sensor_with_controller.led_set(command)

        call_args = sensor_with_controller.controller.mqtt_pub.call_args
        sent_payload = json.loads(call_args[0][1])

        assert "transition" not in sent_payload
        assert "flash" not in sent_payload

    def test_query_command(self, sensor_with_controller):
        """Test QUERY command."""
        sensor_with_controller.reportDrivers = Mock()
        command = {"cmd": "QUERY"}

        sensor_with_controller.query(command)

        sensor_with_controller.reportDrivers.assert_called_once()


class TestMQSensorCheckLimit:
    """Tests for _check_limit helper method."""

    @pytest.fixture
    def sensor(self):
        """Create a MQSensor instance."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        poly.getNode = Mock(return_value=Mock())

        device = {"cmd_topic": "test/cmd"}
        return MQSensor(poly, "controller", "sens1", "Test", device)

    def test_check_limit_within_range(self, sensor):
        """Test values within valid range."""
        assert sensor._check_limit(128) == 128
        assert sensor._check_limit(0) == 0
        assert sensor._check_limit(255) == 255

    def test_check_limit_below_minimum(self, sensor):
        """Test values below minimum are clamped."""
        assert sensor._check_limit(-1) == 0
        assert sensor._check_limit(-100) == 0

    def test_check_limit_above_maximum(self, sensor):
        """Test values above maximum are clamped."""
        assert sensor._check_limit(256) == 255
        assert sensor._check_limit(1000) == 255


class TestMQSensorDriversAndCommands:
    """Tests for node configuration."""

    def test_node_id(self):
        """Test node ID is correct."""
        assert MQSensor.id == "mqsens"

    def test_drivers_configuration(self):
        """Test drivers are properly configured."""
        assert len(MQSensor.drivers) == 10

        driver_names = [d["driver"] for d in MQSensor.drivers]
        expected = ["ST", "CLITEMP", "GPV", "CLIHUM", "LUMIN",
                    "GV0", "GV1", "GV2", "GV3", "GV4"]
        assert driver_names == expected

    def test_commands_configuration(self):
        """Test commands are properly configured."""
        assert "QUERY" in MQSensor.commands
        assert "DON" in MQSensor.commands
        assert "DOF" in MQSensor.commands
        assert "SETLED" in MQSensor.commands

    def test_hint_value(self):
        """Test hint is defined."""
        assert MQSensor.hint == "0x01030200"


class TestMQSensorIntegration:
    """Integration tests for complete workflows."""

    @pytest.fixture
    def full_sensor_setup(self):
        """Create a fully mocked sensor setup."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "home/multisensor/cmd"}
        s = MQSensor(poly, "controller", "multi1", "Multi Sensor", device)
        s.setDriver = Mock()
        s.reportCmd = Mock()
        s.reportDrivers = Mock()

        return s

    def test_motion_detection_workflow(self, full_sensor_setup):
        """Test motion detection workflow."""
        sensor = full_sensor_setup

        # No motion
        payload = json.dumps({"motion": "standby"})
        sensor.updateInfo(payload, "home/multisensor/state")
        assert sensor.motion is False

        # Motion detected
        payload = json.dumps({"motion": "active"})
        sensor.updateInfo(payload, "home/multisensor/state")
        assert sensor.motion is True
        sensor.reportCmd.assert_called_with("DON")

        # Back to standby
        sensor.reportCmd.reset_mock()
        payload = json.dumps({"motion": "standby"})
        sensor.updateInfo(payload, "home/multisensor/state")
        assert sensor.motion is False
        sensor.reportCmd.assert_called_with("DOF")

    def test_environmental_monitoring_workflow(self, full_sensor_setup):
        """Test environmental sensor updates."""
        sensor = full_sensor_setup

        payload = json.dumps({
            "temperature": 72.5,
            "humidity": 55,
            "heatIndex": 74.0,
            "ldr": 800
        })

        sensor.updateInfo(payload, "home/multisensor/state")

        sensor.setDriver.assert_any_call("CLITEMP", 72.5)
        sensor.setDriver.assert_any_call("CLIHUM", 55)
        sensor.setDriver.assert_any_call("GPV", 74.0)
        sensor.setDriver.assert_any_call("LUMIN", 800)

    def test_led_control_workflow(self, full_sensor_setup):
        """Test LED control commands."""
        sensor = full_sensor_setup

        # Turn LED on
        sensor.led_on({"cmd": "DON"})
        assert sensor.controller.mqtt_pub.called

        # Turn LED off
        sensor.controller.mqtt_pub.reset_mock()
        sensor.led_off({"cmd": "DOF"})
        assert sensor.controller.mqtt_pub.called

        # Set LED color
        sensor.controller.mqtt_pub.reset_mock()
        command = {
            "query": {
                "R.uom100": "255",
                "G.uom100": "0",
                "B.uom100": "0",
                "I.uom100": "255"
            }
        }
        sensor.led_set(command)
        assert sensor.controller.mqtt_pub.called

    def test_complete_sensor_update_workflow(self, full_sensor_setup):
        """Test complete sensor data update."""
        sensor = full_sensor_setup

        payload = json.dumps({
            "motion": "active",
            "temperature": 70.0,
            "humidity": 60,
            "heatIndex": 72.0,
            "ldr": 650,
            "state": "ON",
            "brightness": 150,
            "color": {"r": 200, "g": 100, "b": 50}
        })

        sensor.updateInfo(payload, "home/multisensor/state")

        # Verify motion state
        assert sensor.motion is True

        # Verify multiple setDriver calls were made
        assert sensor.setDriver.call_count >= 9
