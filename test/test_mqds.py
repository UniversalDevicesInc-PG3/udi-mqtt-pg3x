"""
Comprehensive test suite for MQds node.

Tests cover:
- Initialization (with/without sensor_id)
- MQTT message handling (JSON payloads with DS18B20 sensor data)
- Temperature processing
- Tasmota StatusSNS wrapper handling
- Multi-sensor support via sensor_id
- Fallback to DS18B20 sensor_id
- Error handling
- Query command
"""

import pytest
from unittest.mock import Mock
from nodes.MQds import MQds, DEFAULT_SENSOR_ID, FALLBACK_SENSOR_ID


class TestMQdsInitialization:
    """Tests for MQds initialization."""

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
        return {"cmd_topic": "home/ds/1/cmd"}

    def test_initialization_basic(self, mock_polyglot, device_config):
        """Test basic MQds initialization without sensor_id."""
        controller = Mock()
        mock_polyglot.getNode.return_value = controller

        ds = MQds(
            mock_polyglot, "controller", "ds_1", "Living Room DS18B20", device_config
        )

        assert ds.id == "mqds"
        assert ds.address == "ds_1"
        assert ds.name == "Living Room DS18B20"
        assert ds.cmd_topic == "home/ds/1/cmd"
        assert ds.sensor_id == DEFAULT_SENSOR_ID
        assert ds.lpfx == "ds_1:Living Room DS18B20"

    def test_initialization_adds_default_sensor_id_to_device(
        self, mock_polyglot, device_config
    ):
        """Test that initialization adds sensor_id to device dict if not present."""
        controller = Mock()
        mock_polyglot.getNode.return_value = controller

        ds = MQds(mock_polyglot, "controller", "ds_1", "DS Sensor", device_config)

        assert device_config["sensor_id"] == DEFAULT_SENSOR_ID

    def test_initialization_with_custom_sensor_id(self, mock_polyglot):
        """Test initialization with custom sensor_id."""
        device = {"cmd_topic": "home/ds/1/cmd", "sensor_id": "DS18B20-1"}
        controller = Mock()
        mock_polyglot.getNode.return_value = controller

        ds = MQds(mock_polyglot, "controller", "ds_1", "DS Sensor", device)

        assert ds.sensor_id == "DS18B20-1"

    def test_initialization_gets_controller(self, mock_polyglot, device_config):
        """Test that initialization retrieves the controller."""
        controller = Mock()
        mock_polyglot.getNode.return_value = controller

        ds = MQds(mock_polyglot, "controller", "ds_1", "Test DS", device_config)

        mock_polyglot.getNode.assert_called_once_with("controller")
        assert ds.controller == controller


class TestMQdsUpdateInfo:
    """Tests for updateInfo method (MQTT message handling)."""

    @pytest.fixture
    def ds(self):
        """Create a MQds instance for testing."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/ds/cmd", "sensor_id": "DS18B20"}
        d = MQds(poly, "controller", "ds1", "Test", device)
        d.setDriver = Mock()

        return d

    def test_update_info_valid_temperature(self, ds):
        """Test receiving valid temperature data."""
        payload = '{"DS18B20": {"Temperature": 72.5}}'
        ds.updateInfo(payload, "test/ds/state")

        ds.setDriver.assert_any_call("ST", 1)
        ds.setDriver.assert_any_call("CLITEMP", 72.5)

    def test_update_info_zero_temperature(self, ds):
        """Test receiving zero temperature (freezing point)."""
        payload = '{"DS18B20": {"Temperature": 0}}'
        ds.updateInfo(payload, "test/ds/state")

        ds.setDriver.assert_any_call("ST", 1)
        ds.setDriver.assert_any_call("CLITEMP", 0)

    def test_update_info_negative_temperature(self, ds):
        """Test receiving negative temperature."""
        payload = '{"DS18B20": {"Temperature": -10.5}}'
        ds.updateInfo(payload, "test/ds/state")

        ds.setDriver.assert_any_call("ST", 1)
        ds.setDriver.assert_any_call("CLITEMP", -10.5)

    def test_update_info_high_temperature(self, ds):
        """Test receiving high temperature."""
        payload = '{"DS18B20": {"Temperature": 212.0}}'
        ds.updateInfo(payload, "test/ds/state")

        ds.setDriver.assert_any_call("ST", 1)
        ds.setDriver.assert_any_call("CLITEMP", 212.0)

    def test_update_info_tasmota_statussns_wrapper(self, ds):
        """Test handling Tasmota StatusSNS wrapper."""
        payload = '{"StatusSNS": {"DS18B20": {"Temperature": 68.5}}}'
        ds.updateInfo(payload, "test/ds/state")

        ds.setDriver.assert_any_call("ST", 1)
        ds.setDriver.assert_any_call("CLITEMP", 68.5)

    def test_update_info_missing_sensor_id_uses_fallback(self, ds):
        """Test that missing sensor_id falls back to FALLBACK_SENSOR_ID."""
        ds.sensor_id = "CustomSensor"
        payload = '{"DS18B20": {"Temperature": 70.0}}'
        ds.updateInfo(payload, "test/ds/state")

        # Should use fallback DS18B20 sensor
        ds.setDriver.assert_any_call("ST", 1)
        ds.setDriver.assert_any_call("CLITEMP", 70.0)

    def test_update_info_no_sensor_data_found(self, ds):
        """Test handling payload without expected sensor_id or fallback."""
        ds.sensor_id = "CustomSensor"
        payload = '{"OtherSensor": {"Temperature": 70.0}}'
        ds.updateInfo(payload, "test/ds/state")

        # Should set status to 0 (error)
        ds.setDriver.assert_called_once_with("ST", 0)

    def test_update_info_sensor_data_not_dict(self, ds):
        """Test handling payload where sensor value is not a dict."""
        payload = '{"DS18B20": "invalid"}'
        ds.updateInfo(payload, "test/ds/state")

        # Should set status to 0 (error)
        ds.setDriver.assert_called_once_with("ST", 0)

    def test_update_info_temperature_key_missing(self, ds):
        """Test handling payload with sensor dict but no Temperature key."""
        payload = '{"DS18B20": {"Humidity": 50.0}}'
        ds.updateInfo(payload, "test/ds/state")

        # Should set status to 0 (error)
        ds.setDriver.assert_called_once_with("ST", 0)

    def test_update_info_temperature_is_none(self, ds):
        """Test handling payload with Temperature key but None value."""
        payload = '{"DS18B20": {"Temperature": null}}'
        ds.updateInfo(payload, "test/ds/state")

        # Should set status to 0 (error)
        ds.setDriver.assert_called_once_with("ST", 0)

    def test_update_info_invalid_json(self, ds):
        """Test handling invalid JSON payload."""
        payload = "not valid json{"
        ds.updateInfo(payload, "test/ds/state")

        # Should not call setDriver
        ds.setDriver.assert_not_called()

    def test_update_info_empty_payload(self, ds):
        """Test handling empty JSON object."""
        payload = "{}"
        ds.updateInfo(payload, "test/ds/state")

        # Should set status to 0 (error)
        ds.setDriver.assert_called_once_with("ST", 0)

    def test_update_info_default_sensor_id(self, ds):
        """Test with DEFAULT_SENSOR_ID."""
        ds.sensor_id = DEFAULT_SENSOR_ID
        payload = f'{{"{DEFAULT_SENSOR_ID}": {{"Temperature": 72.0}}}}'
        ds.updateInfo(payload, "test/ds/state")

        ds.setDriver.assert_any_call("ST", 1)
        ds.setDriver.assert_any_call("CLITEMP", 72.0)

    def test_update_info_multiple_sensors_selects_correct_one(self, ds):
        """Test selecting correct sensor from multi-sensor payload."""
        payload = """{
            "DHT22": {"Temperature": 71.0, "Humidity": 50.0},
            "DS18B20": {"Temperature": 72.0},
            "BMP280": {"Temperature": 70.0}
        }"""
        ds.updateInfo(payload, "test/ds/state")

        # Should use DS18B20 data
        ds.setDriver.assert_any_call("CLITEMP", 72.0)

    def test_update_info_custom_sensor_id_has_priority(self, ds):
        """Test that custom sensor_id takes priority over fallback."""
        ds.sensor_id = "DS18B20-1"
        payload = """{
            "DS18B20-1": {"Temperature": 75.0},
            "DS18B20": {"Temperature": 70.0}
        }"""
        ds.updateInfo(payload, "test/ds/state")

        # Should use DS18B20-1 data (custom), not fallback
        ds.setDriver.assert_any_call("CLITEMP", 75.0)


class TestMQdsQuery:
    """Tests for query command handler."""

    @pytest.fixture
    def ds_with_controller(self):
        """Create a MQds with mocked controller."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/ds/cmd"}
        d = MQds(poly, "controller", "ds1", "Test", device)
        d.reportDrivers = Mock()

        return d

    def test_query_command(self, ds_with_controller):
        """Test QUERY command handler."""
        command = {"cmd": "QUERY"}

        ds_with_controller.query(command)

        # Should publish to Status topic with "10" (Tasmota sensor status)
        ds_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/ds/Status", "10"
        )
        ds_with_controller.reportDrivers.assert_called_once()

    def test_query_without_command(self, ds_with_controller):
        """Test QUERY with None command."""
        ds_with_controller.query(None)

        ds_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/ds/Status", "10"
        )
        ds_with_controller.reportDrivers.assert_called_once()

    def test_query_topic_construction(self, ds_with_controller):
        """Test that query constructs correct topic."""
        ds_with_controller.cmd_topic = "home/living/ds/cmd"
        ds_with_controller.query(None)

        # Should replace last segment with "Status"
        ds_with_controller.controller.mqtt_pub.assert_called_once_with(
            "home/living/ds/Status", "10"
        )


class TestMQdsDriversAndCommands:
    """Tests for node configuration (drivers, commands, etc.)."""

    def test_node_id(self):
        """Test that node ID is correct."""
        assert MQds.id == "mqds"

    def test_drivers_configuration(self):
        """Test drivers are properly configured."""
        assert hasattr(MQds, "drivers")
        assert len(MQds.drivers) == 2

        expected_drivers = {
            "ST": {"value": 0, "uom": 2, "name": "DS18B20 ST"},
            "CLITEMP": {"value": 0, "uom": 17, "name": "Temperature"},
        }

        for driver in MQds.drivers:
            driver_code = driver["driver"]
            assert driver_code in expected_drivers
            expected = expected_drivers[driver_code]
            assert driver["value"] == expected["value"]
            assert driver["uom"] == expected["uom"]
            assert driver["name"] == expected["name"]

    def test_commands_configuration(self):
        """Test commands are properly configured."""
        assert hasattr(MQds, "commands")
        assert "QUERY" in MQds.commands
        assert MQds.commands["QUERY"] == MQds.query


class TestMQdsConstants:
    """Tests for module constants."""

    def test_default_sensor_id(self):
        """Test default sensor ID constant."""
        assert DEFAULT_SENSOR_ID == "SINGLE_SENSOR"

    def test_fallback_sensor_id(self):
        """Test fallback sensor ID constant."""
        assert FALLBACK_SENSOR_ID == "DS18B20"

    def test_sensor_ids_are_different(self):
        """Test that default and fallback IDs are different."""
        assert DEFAULT_SENSOR_ID != FALLBACK_SENSOR_ID


class TestMQdsIntegration:
    """Integration tests for complete workflows."""

    @pytest.fixture
    def full_ds_setup(self):
        """Create a fully mocked DS setup."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "home/bedroom/ds/cmd", "sensor_id": "DS18B20"}
        d = MQds(poly, "controller", "ds1", "Bedroom DS18B20", device)
        d.setDriver = Mock()
        d.reportDrivers = Mock()

        return d

    def test_full_sensor_reading_workflow(self, full_ds_setup):
        """Test complete sensor reading workflow."""
        ds = full_ds_setup

        # Device publishes temperature data
        payload = '{"DS18B20": {"Temperature": 72.5}}'
        ds.updateInfo(payload, "home/bedroom/ds/state")

        # Verify data was processed
        ds.setDriver.assert_any_call("ST", 1)
        ds.setDriver.assert_any_call("CLITEMP", 72.5)

    def test_query_workflow(self, full_ds_setup):
        """Test query workflow."""
        ds = full_ds_setup

        # Query current state
        ds.query(None)

        # Should request sensor status via Tasmota command
        ds.controller.mqtt_pub.assert_called_with("home/bedroom/ds/Status", "10")
        ds.reportDrivers.assert_called_once()

    def test_tasmota_integration_workflow(self, full_ds_setup):
        """Test complete Tasmota integration workflow."""
        ds = full_ds_setup

        # Query device
        ds.query(None)
        ds.controller.mqtt_pub.assert_called_with("home/bedroom/ds/Status", "10")

        # Device responds with Tasmota StatusSNS format
        payload = '{"StatusSNS": {"DS18B20": {"Temperature": 68.5}}}'
        ds.updateInfo(payload, "home/bedroom/ds/state")

        # Verify data was extracted correctly
        ds.setDriver.assert_any_call("CLITEMP", 68.5)

    def test_error_recovery_workflow(self, full_ds_setup):
        """Test error recovery from invalid messages."""
        ds = full_ds_setup

        # Receive valid data first
        payload = '{"DS18B20": {"Temperature": 70.0}}'
        ds.updateInfo(payload, "home/bedroom/ds/state")
        ds.setDriver.reset_mock()

        # Receive invalid JSON
        ds.updateInfo("invalid json", "home/bedroom/ds/state")
        ds.setDriver.assert_not_called()

        # Valid update should still work
        ds.updateInfo(payload, "home/bedroom/ds/state")
        ds.setDriver.assert_any_call("ST", 1)

    def test_sensor_offline_workflow(self, full_ds_setup):
        """Test handling sensor going offline."""
        ds = full_ds_setup

        # Sensor online with data
        payload = '{"DS18B20": {"Temperature": 70.0}}'
        ds.updateInfo(payload, "home/bedroom/ds/state")
        ds.setDriver.reset_mock()

        # Sensor goes offline (missing from payload)
        payload = '{"OtherSensor": {"Temperature": 70.0}}'
        ds.updateInfo(payload, "home/bedroom/ds/state")

        # Should set status to 0
        ds.setDriver.assert_called_once_with("ST", 0)

    def test_multi_sensor_device_workflow(self, full_ds_setup):
        """Test device with multiple sensors."""
        ds = full_ds_setup

        # Device has multiple sensors, but we only care about DS18B20
        payload = """{
            "DHT22": {"Temperature": 71.0, "Humidity": 50.0},
            "DS18B20": {"Temperature": 72.0},
            "BMP280": {"Temperature": 70.0}
        }"""
        ds.updateInfo(payload, "home/bedroom/ds/state")

        # Should only use DS18B20 data
        ds.setDriver.assert_any_call("CLITEMP", 72.0)

    def test_temperature_change_monitoring_workflow(self, full_ds_setup):
        """Test monitoring temperature changes over time."""
        ds = full_ds_setup

        # Initial reading
        ds.updateInfo('{"DS18B20": {"Temperature": 70.0}}', "home/bedroom/ds/state")
        ds.setDriver.assert_any_call("CLITEMP", 70.0)
        ds.setDriver.reset_mock()

        # Temperature rises
        ds.updateInfo('{"DS18B20": {"Temperature": 75.0}}', "home/bedroom/ds/state")
        ds.setDriver.assert_any_call("CLITEMP", 75.0)
        ds.setDriver.reset_mock()

        # Temperature drops
        ds.updateInfo('{"DS18B20": {"Temperature": 65.0}}', "home/bedroom/ds/state")
        ds.setDriver.assert_any_call("CLITEMP", 65.0)

    def test_fallback_sensor_workflow(self, full_ds_setup):
        """Test fallback to DS18B20 when custom sensor_id not found."""
        ds = full_ds_setup
        ds.sensor_id = "CustomDS"

        # Custom sensor not in payload, but DS18B20 is
        payload = '{"DS18B20": {"Temperature": 72.0}}'
        ds.updateInfo(payload, "home/bedroom/ds/state")

        # Should use fallback DS18B20
        ds.setDriver.assert_any_call("ST", 1)
        ds.setDriver.assert_any_call("CLITEMP", 72.0)

    def test_extreme_temperature_workflow(self, full_ds_setup):
        """Test various extreme temperature scenarios."""
        ds = full_ds_setup

        # Very cold
        ds.updateInfo('{"DS18B20": {"Temperature": -40.0}}', "home/bedroom/ds/state")
        ds.setDriver.assert_any_call("CLITEMP", -40.0)
        ds.setDriver.reset_mock()

        # Very hot
        ds.updateInfo('{"DS18B20": {"Temperature": 257.0}}', "home/bedroom/ds/state")
        ds.setDriver.assert_any_call("CLITEMP", 257.0)
        ds.setDriver.reset_mock()

        # Freezing point
        ds.updateInfo('{"DS18B20": {"Temperature": 32.0}}', "home/bedroom/ds/state")
        ds.setDriver.assert_any_call("CLITEMP", 32.0)
        ds.setDriver.reset_mock()

        # Boiling point
        ds.updateInfo('{"DS18B20": {"Temperature": 212.0}}', "home/bedroom/ds/state")
        ds.setDriver.assert_any_call("CLITEMP", 212.0)
