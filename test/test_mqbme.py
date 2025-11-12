"""
Comprehensive test suite for MQbme node.

Tests cover:
- Initialization (with/without sensor_id)
- MQTT message handling (JSON payloads with BME280 sensor data)
- Temperature, Humidity, Pressure, and Dew Point processing
- Tasmota StatusSNS wrapper handling
- Pressure conversion (hPa to inHg)
- Multi-sensor support via sensor_id
- Error handling
- Query command
"""

import pytest
from unittest.mock import Mock
from nodes.MQbme import MQbme, HPA_TO_INHG, DEFAULT_SENSOR_ID


class TestMQbmeInitialization:
    """Tests for MQbme initialization."""

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
        return {"cmd_topic": "home/bme/1/cmd"}

    def test_initialization_basic(self, mock_polyglot, device_config):
        """Test basic MQbme initialization without sensor_id."""
        controller = Mock()
        mock_polyglot.getNode.return_value = controller

        bme = MQbme(
            mock_polyglot, "controller", "bme_1", "Living Room BME", device_config
        )

        assert bme.id == "mqbme"
        assert bme.address == "bme_1"
        assert bme.name == "Living Room BME"
        assert bme.cmd_topic == "home/bme/1/cmd"
        assert bme.sensor_id == DEFAULT_SENSOR_ID
        assert bme.lpfx == "bme_1:Living Room BME"

    def test_initialization_adds_default_sensor_id_to_device(
        self, mock_polyglot, device_config
    ):
        """Test that initialization adds sensor_id to device dict if not present."""
        controller = Mock()
        mock_polyglot.getNode.return_value = controller

        _bme = MQbme(mock_polyglot, "controller", "bme_1", "BME Sensor", device_config)

        assert device_config["sensor_id"] == DEFAULT_SENSOR_ID

    def test_initialization_with_custom_sensor_id(self, mock_polyglot):
        """Test initialization with custom sensor_id."""
        device = {"cmd_topic": "home/bme/1/cmd", "sensor_id": "BME280"}
        controller = Mock()
        mock_polyglot.getNode.return_value = controller

        bme = MQbme(mock_polyglot, "controller", "bme_1", "BME Sensor", device)

        assert bme.sensor_id == "BME280"

    def test_initialization_gets_controller(self, mock_polyglot, device_config):
        """Test that initialization retrieves the controller."""
        controller = Mock()
        mock_polyglot.getNode.return_value = controller

        bme = MQbme(mock_polyglot, "controller", "bme_1", "Test BME", device_config)

        mock_polyglot.getNode.assert_called_once_with("controller")
        assert bme.controller == controller


class TestMQbmeUpdateInfo:
    """Tests for updateInfo method (MQTT message handling)."""

    @pytest.fixture
    def bme(self):
        """Create a MQbme instance for testing."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/bme/cmd", "sensor_id": "BME280"}
        b = MQbme(poly, "controller", "bme1", "Test", device)
        b.setDriver = Mock()

        return b

    def test_update_info_complete_sensor_data(self, bme):
        """Test receiving complete BME280 sensor data."""
        payload = """{
            "BME280": {
                "Temperature": 72.5,
                "Humidity": 45.0,
                "DewPoint": 50.2,
                "Pressure": 1013.25
            }
        }"""
        bme.updateInfo(payload, "test/bme/state")

        # Verify all drivers were set
        assert bme.setDriver.call_count == 5
        bme.setDriver.assert_any_call("ST", 1)
        bme.setDriver.assert_any_call("CLITEMP", 72.5)
        bme.setDriver.assert_any_call("CLIHUM", 45.0)
        bme.setDriver.assert_any_call("DEWPT", 50.2)
        bme.setDriver.assert_any_call("BARPRES", 29.92)

    def test_update_info_without_pressure(self, bme):
        """Test receiving sensor data without pressure."""
        payload = """{
            "BME280": {
                "Temperature": 70.0,
                "Humidity": 50.0,
                "DewPoint": 52.0
            }
        }"""
        bme.updateInfo(payload, "test/bme/state")

        # Should set temperature, humidity, dew point but not pressure
        bme.setDriver.assert_any_call("ST", 1)
        bme.setDriver.assert_any_call("CLITEMP", 70.0)
        bme.setDriver.assert_any_call("CLIHUM", 50.0)
        bme.setDriver.assert_any_call("DEWPT", 52.0)
        # Should not set BARPRES
        assert not any(call[0][0] == "BARPRES" for call in bme.setDriver.call_args_list)

    def test_update_info_tasmota_statussns_wrapper(self, bme):
        """Test handling Tasmota StatusSNS wrapper."""
        payload = """{
            "StatusSNS": {
                "BME280": {
                    "Temperature": 68.5,
                    "Humidity": 55.0,
                    "DewPoint": 53.0,
                    "Pressure": 1020.5
                }
            }
        }"""
        bme.updateInfo(payload, "test/bme/state")

        bme.setDriver.assert_any_call("ST", 1)
        bme.setDriver.assert_any_call("CLITEMP", 68.5)
        bme.setDriver.assert_any_call("CLIHUM", 55.0)

    def test_update_info_missing_sensor_id(self, bme):
        """Test handling payload without expected sensor_id."""
        payload = '{"OtherSensor": {"Temperature": 70.0}}'
        bme.updateInfo(payload, "test/bme/state")

        # Should set status to 0 (error)
        bme.setDriver.assert_called_once_with("ST", 0)

    def test_update_info_sensor_data_not_dict(self, bme):
        """Test handling payload where sensor value is not a dict."""
        payload = '{"BME280": "invalid"}'
        bme.updateInfo(payload, "test/bme/state")

        # Should set status to 0 (error)
        bme.setDriver.assert_called_once_with("ST", 0)

    def test_update_info_invalid_json(self, bme):
        """Test handling invalid JSON payload."""
        payload = "not valid json{"
        bme.updateInfo(payload, "test/bme/state")

        # Should not call setDriver
        bme.setDriver.assert_not_called()

    def test_update_info_empty_sensor_data(self, bme):
        """Test handling empty sensor data dict."""
        payload = '{"BME280": {}}'
        bme.updateInfo(payload, "test/bme/state")

        # Should set status to 1 but with None values
        bme.setDriver.assert_any_call("ST", 1)
        bme.setDriver.assert_any_call("CLITEMP", None)
        bme.setDriver.assert_any_call("CLIHUM", None)
        bme.setDriver.assert_any_call("DEWPT", None)

    def test_update_info_partial_sensor_data(self, bme):
        """Test handling partial sensor data (only some fields)."""
        payload = '{"BME280": {"Temperature": 75.0, "Humidity": 40.0}}'
        bme.updateInfo(payload, "test/bme/state")

        bme.setDriver.assert_any_call("ST", 1)
        bme.setDriver.assert_any_call("CLITEMP", 75.0)
        bme.setDriver.assert_any_call("CLIHUM", 40.0)
        bme.setDriver.assert_any_call("DEWPT", None)

    def test_update_info_default_sensor_id(self, bme):
        """Test with DEFAULT_SENSOR_ID."""
        bme.sensor_id = DEFAULT_SENSOR_ID
        payload = f'{{"{DEFAULT_SENSOR_ID}": {{"Temperature": 72.0}}}}'
        bme.updateInfo(payload, "test/bme/state")

        bme.setDriver.assert_any_call("ST", 1)
        bme.setDriver.assert_any_call("CLITEMP", 72.0)

    def test_update_info_multiple_sensors_selects_correct_one(self, bme):
        """Test selecting correct sensor from multi-sensor payload."""
        payload = """{
            "BME280": {
                "Temperature": 72.0,
                "Humidity": 45.0
            },
            "DHT22": {
                "Temperature": 71.0,
                "Humidity": 50.0
            }
        }"""
        bme.updateInfo(payload, "test/bme/state")

        # Should use BME280 data, not DHT22
        bme.setDriver.assert_any_call("CLITEMP", 72.0)
        bme.setDriver.assert_any_call("CLIHUM", 45.0)


class TestMQbmePressureConversion:
    """Tests for pressure conversion method."""

    @pytest.fixture
    def bme(self):
        """Create a MQbme instance for testing."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/bme/cmd"}
        b = MQbme(poly, "controller", "bme1", "Test", device)

        return b

    def test_convert_pressure_valid_value(self, bme):
        """Test converting valid pressure value."""
        result = bme._convert_pressure(1013.25)
        assert result == pytest.approx(29.92, rel=0.01)

    def test_convert_pressure_zero(self, bme):
        """Test converting zero pressure."""
        result = bme._convert_pressure(0)
        assert result == 0.0

    def test_convert_pressure_string_number(self, bme):
        """Test converting string number."""
        result = bme._convert_pressure("1013.25")
        assert result == pytest.approx(29.92, rel=0.01)

    def test_convert_pressure_invalid_string(self, bme):
        """Test converting invalid string."""
        result = bme._convert_pressure("invalid")
        assert result is None

    def test_convert_pressure_none(self, bme):
        """Test converting None."""
        result = bme._convert_pressure(None)
        assert result is None

    def test_convert_pressure_high_value(self, bme):
        """Test converting high pressure value."""
        result = bme._convert_pressure(1050.0)
        assert result == pytest.approx(31.00, rel=0.01)

    def test_convert_pressure_low_value(self, bme):
        """Test converting low pressure value."""
        result = bme._convert_pressure(980.0)
        assert result == pytest.approx(28.94, rel=0.01)

    def test_convert_pressure_rounding(self, bme):
        """Test that result is rounded to 2 decimal places."""
        result = bme._convert_pressure(1013.25678)
        # Should round to 2 decimal places
        assert len(str(result).split(".")[1]) <= 2


class TestMQbmeQuery:
    """Tests for query command handler."""

    @pytest.fixture
    def bme_with_controller(self):
        """Create a MQbme with mocked controller."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "test/bme/cmd"}
        b = MQbme(poly, "controller", "bme1", "Test", device)
        b.reportDrivers = Mock()

        return b

    def test_query_command(self, bme_with_controller):
        """Test QUERY command handler."""
        command = {"cmd": "QUERY"}

        bme_with_controller.query(command)

        # Should publish to Status topic with "10" (Tasmota sensor status)
        bme_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/bme/Status", "10"
        )
        bme_with_controller.reportDrivers.assert_called_once()

    def test_query_without_command(self, bme_with_controller):
        """Test QUERY with None command."""
        bme_with_controller.query(None)

        bme_with_controller.controller.mqtt_pub.assert_called_once_with(
            "test/bme/Status", "10"
        )
        bme_with_controller.reportDrivers.assert_called_once()

    def test_query_topic_construction(self, bme_with_controller):
        """Test that query constructs correct topic."""
        bme_with_controller.cmd_topic = "home/living/bme/cmd"
        bme_with_controller.query(None)

        # Should replace last segment with "Status"
        bme_with_controller.controller.mqtt_pub.assert_called_once_with(
            "home/living/bme/Status", "10"
        )


class TestMQbmeDriversAndCommands:
    """Tests for node configuration (drivers, commands, etc.)."""

    def test_node_id(self):
        """Test that node ID is correct."""
        assert MQbme.id == "mqbme"

    def test_drivers_configuration(self):
        """Test drivers are properly configured."""
        assert hasattr(MQbme, "drivers")
        assert len(MQbme.drivers) == 5

        expected_drivers = {
            "ST": {"value": 0, "uom": 2, "name": "Status"},
            "CLITEMP": {"value": 0, "uom": 17, "name": "Temperature"},
            "CLIHUM": {"value": 0, "uom": 22, "name": "Humidity"},
            "DEWPT": {"value": 0, "uom": 17, "name": "Dew Point"},
            "BARPRES": {"value": 0, "uom": 23, "name": "Barometric Pressure"},
        }

        for driver in MQbme.drivers:
            driver_code = driver["driver"]
            assert driver_code in expected_drivers
            expected = expected_drivers[driver_code]
            assert driver["value"] == expected["value"]
            assert driver["uom"] == expected["uom"]
            assert driver["name"] == expected["name"]

    def test_commands_configuration(self):
        """Test commands are properly configured."""
        assert hasattr(MQbme, "commands")
        assert "QUERY" in MQbme.commands
        assert MQbme.commands["QUERY"] == MQbme.query


class TestMQbmeConstants:
    """Tests for module constants."""

    def test_hpa_to_inhg_conversion_factor(self):
        """Test pressure conversion constant."""
        assert HPA_TO_INHG == pytest.approx(0.02952998751)

    def test_default_sensor_id(self):
        """Test default sensor ID constant."""
        assert DEFAULT_SENSOR_ID == "SINGLE_SENSOR"

    def test_pressure_conversion_accuracy(self):
        """Test that conversion constant produces accurate results."""
        # Standard atmospheric pressure: 1013.25 hPa = 29.92 inHg
        result = 1013.25 * HPA_TO_INHG
        assert result == pytest.approx(29.92, rel=0.01)


class TestMQbmeIntegration:
    """Integration tests for complete workflows."""

    @pytest.fixture
    def full_bme_setup(self):
        """Create a fully mocked BME setup."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        controller = Mock()
        controller.mqtt_pub = Mock()
        poly.getNode.return_value = controller

        device = {"cmd_topic": "home/bedroom/bme/cmd", "sensor_id": "BME280"}
        b = MQbme(poly, "controller", "bme1", "Bedroom BME", device)
        b.setDriver = Mock()
        b.reportDrivers = Mock()

        return b

    def test_full_sensor_reading_workflow(self, full_bme_setup):
        """Test complete sensor reading workflow."""
        bme = full_bme_setup

        # Device publishes sensor data
        payload = """{
            "BME280": {
                "Temperature": 72.5,
                "Humidity": 45.0,
                "DewPoint": 50.2,
                "Pressure": 1013.25
            }
        }"""
        bme.updateInfo(payload, "home/bedroom/bme/state")

        # Verify all data was processed
        assert bme.setDriver.call_count == 5
        bme.setDriver.assert_any_call("ST", 1)
        bme.setDriver.assert_any_call("CLITEMP", 72.5)
        bme.setDriver.assert_any_call("CLIHUM", 45.0)
        bme.setDriver.assert_any_call("DEWPT", 50.2)
        bme.setDriver.assert_any_call("BARPRES", 29.92)

    def test_query_workflow(self, full_bme_setup):
        """Test query workflow."""
        bme = full_bme_setup

        # Query current state
        bme.query(None)

        # Should request sensor status via Tasmota command
        bme.controller.mqtt_pub.assert_called_with("home/bedroom/bme/Status", "10")
        bme.reportDrivers.assert_called_once()

    def test_tasmota_integration_workflow(self, full_bme_setup):
        """Test complete Tasmota integration workflow."""
        bme = full_bme_setup

        # Query device
        bme.query(None)
        bme.controller.mqtt_pub.assert_called_with("home/bedroom/bme/Status", "10")

        # Device responds with Tasmota StatusSNS format
        payload = """{
            "StatusSNS": {
                "BME280": {
                    "Temperature": 68.5,
                    "Humidity": 55.0,
                    "DewPoint": 53.0,
                    "Pressure": 1020.5
                }
            }
        }"""
        bme.updateInfo(payload, "home/bedroom/bme/state")

        # Verify data was extracted correctly
        bme.setDriver.assert_any_call("CLITEMP", 68.5)
        bme.setDriver.assert_any_call("CLIHUM", 55.0)
        bme.setDriver.assert_any_call("DEWPT", 53.0)

    def test_error_recovery_workflow(self, full_bme_setup):
        """Test error recovery from invalid messages."""
        bme = full_bme_setup

        # Receive valid data first
        payload = '{"BME280": {"Temperature": 70.0, "Humidity": 50.0}}'
        bme.updateInfo(payload, "home/bedroom/bme/state")
        bme.setDriver.reset_mock()

        # Receive invalid JSON
        bme.updateInfo("invalid json", "home/bedroom/bme/state")
        bme.setDriver.assert_not_called()

        # Valid update should still work
        bme.updateInfo(payload, "home/bedroom/bme/state")
        bme.setDriver.assert_any_call("ST", 1)

    def test_sensor_offline_workflow(self, full_bme_setup):
        """Test handling sensor going offline."""
        bme = full_bme_setup

        # Sensor online with data
        payload = '{"BME280": {"Temperature": 70.0, "Humidity": 50.0}}'
        bme.updateInfo(payload, "home/bedroom/bme/state")
        bme.setDriver.reset_mock()

        # Sensor goes offline (missing from payload)
        payload = '{"OtherSensor": {"Temperature": 70.0}}'
        bme.updateInfo(payload, "home/bedroom/bme/state")

        # Should set status to 0
        bme.setDriver.assert_called_once_with("ST", 0)

    def test_multi_sensor_device_workflow(self, full_bme_setup):
        """Test device with multiple sensors."""
        bme = full_bme_setup

        # Device has multiple sensors, but we only care about BME280
        payload = """{
            "DHT22": {
                "Temperature": 71.0,
                "Humidity": 50.0
            },
            "BME280": {
                "Temperature": 72.0,
                "Humidity": 45.0,
                "DewPoint": 50.0,
                "Pressure": 1013.0
            },
            "DS18B20": {
                "Temperature": 70.0
            }
        }"""
        bme.updateInfo(payload, "home/bedroom/bme/state")

        # Should only use BME280 data
        bme.setDriver.assert_any_call("CLITEMP", 72.0)
        bme.setDriver.assert_any_call("CLIHUM", 45.0)

    def test_weather_conditions_workflow(self, full_bme_setup):
        """Test various weather condition scenarios."""
        bme = full_bme_setup

        # Hot and humid
        payload = """{
            "BME280": {
                "Temperature": 95.0,
                "Humidity": 80.0,
                "DewPoint": 88.0,
                "Pressure": 1008.0
            }
        }"""
        bme.updateInfo(payload, "home/bedroom/bme/state")
        bme.setDriver.assert_any_call("CLITEMP", 95.0)

        bme.setDriver.reset_mock()

        # Cold and dry
        payload = """{
            "BME280": {
                "Temperature": 32.0,
                "Humidity": 20.0,
                "DewPoint": 5.0,
                "Pressure": 1030.0
            }
        }"""
        bme.updateInfo(payload, "home/bedroom/bme/state")
        bme.setDriver.assert_any_call("CLITEMP", 32.0)
        bme.setDriver.assert_any_call("CLIHUM", 20.0)
