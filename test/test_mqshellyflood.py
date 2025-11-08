"""
Comprehensive test suite for MQShellyFlood node.

Tests cover:
- Initialization
- Multiple topic handling (temperature, flood, battery, error)
- Topic suffix parsing
- Boolean flood detection
- Query command
- Unknown topic handling
- Edge cases
"""

import pytest
from unittest.mock import Mock
from nodes.MQShellyFlood import MQShellyFlood, TOPIC_MAP


class TestMQShellyFloodInitialization:
    """Tests for MQShellyFlood initialization."""

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
        return {"status_topic": ["home/flood/temperature", "home/flood/flood"]}

    def test_initialization_basic(self, mock_polyglot, device_config):
        """Test basic MQShellyFlood initialization."""
        sensor = MQShellyFlood(
            mock_polyglot, "controller", "flood_1", "Basement Sensor", device_config
        )

        assert sensor.id == "mqshflood"
        assert sensor.address == "flood_1"
        assert sensor.name == "Basement Sensor"
        assert sensor.lpfx == "flood_1:Basement Sensor"

    def test_initialization_minimal(self, mock_polyglot):
        """Test initialization with minimal config."""
        device = {}

        sensor = MQShellyFlood(mock_polyglot, "controller", "flood_2", "Flood", device)

        assert sensor.id == "mqshflood"


class TestMQShellyFloodUpdateInfo:
    """Tests for updateInfo method (MQTT message handling)."""

    @pytest.fixture
    def sensor(self):
        """Create a MQShellyFlood instance for testing."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        poly.getNode = Mock()

        device = {}
        s = MQShellyFlood(poly, "controller", "flood1", "Test", device)
        s.setDriver = Mock()

        return s

    def test_update_info_temperature(self, sensor):
        """Test handling temperature topic."""
        sensor.updateInfo("72.5", "home/sensor/temperature")

        # Should set CLITEMP driver and ST to online
        calls = sensor.setDriver.call_args_list
        assert len(calls) == 2
        assert calls[0] == (("CLITEMP", "72.5"),)
        assert calls[1] == (("ST", 1),)

    def test_update_info_flood_true(self, sensor):
        """Test handling flood detection (true)."""
        sensor.updateInfo("true", "home/sensor/flood")

        # Should set GV0 to 1 for flood detected
        calls = sensor.setDriver.call_args_list
        assert len(calls) == 2
        assert calls[0] == (("GV0", 1),)
        assert calls[1] == (("ST", 1),)

    def test_update_info_flood_false(self, sensor):
        """Test handling flood detection (false)."""
        sensor.updateInfo("false", "home/sensor/flood")

        # Should set GV0 to 0 for no flood
        calls = sensor.setDriver.call_args_list
        assert len(calls) == 2
        assert calls[0] == (("GV0", 0),)
        assert calls[1] == (("ST", 1),)

    def test_update_info_flood_uppercase_true(self, sensor):
        """Test handling flood with uppercase TRUE."""
        sensor.updateInfo("TRUE", "home/sensor/flood")

        # Should handle case-insensitive comparison
        calls = sensor.setDriver.call_args_list
        assert calls[0] == (("GV0", 1),)

    def test_update_info_flood_mixed_case(self, sensor):
        """Test handling flood with mixed case True."""
        sensor.updateInfo("True", "home/sensor/flood")

        calls = sensor.setDriver.call_args_list
        assert calls[0] == (("GV0", 1),)

    def test_update_info_flood_invalid_value(self, sensor):
        """Test handling flood with invalid value (not true/false)."""
        sensor.updateInfo("maybe", "home/sensor/flood")

        # Should set GV0 to 0 for anything other than "true"
        calls = sensor.setDriver.call_args_list
        assert calls[0] == (("GV0", 0),)

    def test_update_info_battery(self, sensor):
        """Test handling battery level topic."""
        sensor.updateInfo("85", "home/sensor/battery")

        # Should set BATLVL driver
        calls = sensor.setDriver.call_args_list
        assert len(calls) == 2
        assert calls[0] == (("BATLVL", "85"),)
        assert calls[1] == (("ST", 1),)

    def test_update_info_error(self, sensor):
        """Test handling error topic."""
        sensor.updateInfo("0", "home/sensor/error")

        # Should set GPV driver
        calls = sensor.setDriver.call_args_list
        assert len(calls) == 2
        assert calls[0] == (("GPV", "0"),)
        assert calls[1] == (("ST", 1),)

    def test_update_info_unknown_topic(self, sensor):
        """Test handling unknown topic suffix."""
        sensor.updateInfo("value", "home/sensor/unknown")

        # Should not set any drivers
        sensor.setDriver.assert_not_called()

    def test_update_info_complex_topic_path(self, sensor):
        """Test handling topic with multiple path segments."""
        sensor.updateInfo("68.0", "shellies/shelly-flood-1/sensor/temperature")

        # Should extract "temperature" suffix correctly
        calls = sensor.setDriver.call_args_list
        assert calls[0] == (("CLITEMP", "68.0"),)

    def test_update_info_single_segment_topic(self, sensor):
        """Test handling single-segment topic."""
        sensor.updateInfo("50", "battery")

        # Should still work with just the suffix
        calls = sensor.setDriver.call_args_list
        assert calls[0] == (("BATLVL", "50"),)

    def test_update_info_multiple_updates(self, sensor):
        """Test multiple sequential updates."""
        # Temperature update
        sensor.updateInfo("70", "home/sensor/temperature")
        assert sensor.setDriver.call_args_list[0] == (("CLITEMP", "70"),)

        sensor.setDriver.reset_mock()

        # Battery update
        sensor.updateInfo("90", "home/sensor/battery")
        assert sensor.setDriver.call_args_list[0] == (("BATLVL", "90"),)

        sensor.setDriver.reset_mock()

        # Flood update
        sensor.updateInfo("true", "home/sensor/flood")
        assert sensor.setDriver.call_args_list[0] == (("GV0", 1),)

    def test_update_info_all_sensors(self, sensor):
        """Test updating all sensors in sequence."""
        topics_and_values = [
            ("temperature", "75.5", "CLITEMP", "75.5"),
            ("flood", "false", "GV0", 0),
            ("battery", "95", "BATLVL", "95"),
            ("error", "0", "GPV", "0"),
        ]

        for topic_suffix, payload, expected_driver, expected_value in topics_and_values:
            sensor.setDriver.reset_mock()
            sensor.updateInfo(payload, f"home/sensor/{topic_suffix}")

            calls = sensor.setDriver.call_args_list
            assert calls[0] == ((expected_driver, expected_value),)
            assert calls[1] == (("ST", 1),)  # Always sets online status


class TestMQShellyFloodCommands:
    """Tests for command handlers."""

    @pytest.fixture
    def sensor_with_controller(self):
        """Create a MQShellyFlood with mocked controller."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        poly.getNode = Mock()

        device = {}
        s = MQShellyFlood(poly, "controller", "flood1", "Test", device)
        s.reportDrivers = Mock()

        return s

    def test_query_command(self, sensor_with_controller):
        """Test QUERY command handler."""
        command = {"cmd": "QUERY"}

        sensor_with_controller.query(command)

        # Should report current drivers
        sensor_with_controller.reportDrivers.assert_called_once()

    def test_query_without_command(self, sensor_with_controller):
        """Test QUERY with None command."""
        sensor_with_controller.query(None)

        sensor_with_controller.reportDrivers.assert_called_once()


class TestMQShellyFloodDriversAndCommands:
    """Tests for node configuration (drivers, commands, etc.)."""

    def test_node_id(self):
        """Test that node ID is correct."""
        assert MQShellyFlood.id == "mqshflood"

    def test_drivers_configuration(self):
        """Test drivers are properly configured."""
        assert hasattr(MQShellyFlood, "drivers")
        assert len(MQShellyFlood.drivers) == 5

        # Check ST driver
        st_driver = MQShellyFlood.drivers[0]
        assert st_driver["driver"] == "ST"
        assert st_driver["value"] == 0
        assert st_driver["uom"] == 2
        assert st_driver["name"] == "Status"

        # Check CLITEMP driver
        temp_driver = MQShellyFlood.drivers[1]
        assert temp_driver["driver"] == "CLITEMP"
        assert temp_driver["uom"] == 17  # Fahrenheit

        # Check GV0 driver (flood)
        flood_driver = MQShellyFlood.drivers[2]
        assert flood_driver["driver"] == "GV0"
        assert flood_driver["uom"] == 2  # Boolean

        # Check BATLVL driver
        battery_driver = MQShellyFlood.drivers[3]
        assert battery_driver["driver"] == "BATLVL"
        assert battery_driver["uom"] == 51  # Percent

        # Check GPV driver (error)
        error_driver = MQShellyFlood.drivers[4]
        assert error_driver["driver"] == "GPV"
        assert error_driver["uom"] == 56  # Raw value

    def test_commands_configuration(self):
        """Test commands are properly configured."""
        assert hasattr(MQShellyFlood, "commands")
        assert "QUERY" in MQShellyFlood.commands
        assert MQShellyFlood.commands["QUERY"] == MQShellyFlood.query


class TestMQShellyFloodConstants:
    """Tests for module constants."""

    def test_topic_map_completeness(self):
        """Test that TOPIC_MAP contains expected keys."""
        expected_keys = ["temperature", "flood", "battery", "error"]

        for key in expected_keys:
            assert key in TOPIC_MAP, f"Missing key: {key}"

    def test_topic_map_values(self):
        """Test TOPIC_MAP driver mappings."""
        assert TOPIC_MAP["temperature"] == "CLITEMP"
        assert TOPIC_MAP["flood"] == "GV0"
        assert TOPIC_MAP["battery"] == "BATLVL"
        assert TOPIC_MAP["error"] == "GPV"

    def test_topic_map_values_unique(self):
        """Test that all TOPIC_MAP values are unique."""
        values = list(TOPIC_MAP.values())
        assert len(values) == len(set(values)), "TOPIC_MAP has duplicate values"


class TestMQShellyFloodIntegration:
    """Integration tests for complete workflows."""

    @pytest.fixture
    def full_sensor_setup(self):
        """Create a fully mocked sensor setup."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        poly.getNode = Mock()

        device = {}
        s = MQShellyFlood(poly, "controller", "basement", "Basement Flood", device)
        s.setDriver = Mock()
        s.reportDrivers = Mock()

        return s

    def test_normal_operation_workflow(self, full_sensor_setup):
        """Test normal operation with no flood."""
        sensor = full_sensor_setup

        # Temperature reading
        sensor.updateInfo("68.0", "shellies/flood-1/temperature")
        assert sensor.setDriver.call_args_list[0] == (("CLITEMP", "68.0"),)

        sensor.setDriver.reset_mock()

        # No flood detected
        sensor.updateInfo("false", "shellies/flood-1/flood")
        assert sensor.setDriver.call_args_list[0] == (("GV0", 0),)

        sensor.setDriver.reset_mock()

        # Good battery level
        sensor.updateInfo("100", "shellies/flood-1/battery")
        assert sensor.setDriver.call_args_list[0] == (("BATLVL", "100"),)

    def test_flood_detected_workflow(self, full_sensor_setup):
        """Test flood detection scenario."""
        sensor = full_sensor_setup

        # Normal state
        sensor.updateInfo("false", "shellies/flood-1/flood")
        assert sensor.setDriver.call_args_list[0] == (("GV0", 0),)

        sensor.setDriver.reset_mock()

        # Flood detected!
        sensor.updateInfo("true", "shellies/flood-1/flood")
        assert sensor.setDriver.call_args_list[0] == (("GV0", 1),)
        assert sensor.setDriver.call_args_list[1] == (("ST", 1),)

    def test_low_battery_workflow(self, full_sensor_setup):
        """Test low battery scenario."""
        sensor = full_sensor_setup

        # Battery draining
        sensor.updateInfo("50", "shellies/flood-1/battery")
        assert sensor.setDriver.call_args_list[0] == (("BATLVL", "50"),)

        sensor.setDriver.reset_mock()

        sensor.updateInfo("25", "shellies/flood-1/battery")
        assert sensor.setDriver.call_args_list[0] == (("BATLVL", "25"),)

        sensor.setDriver.reset_mock()

        sensor.updateInfo("10", "shellies/flood-1/battery")
        assert sensor.setDriver.call_args_list[0] == (("BATLVL", "10"),)

    def test_error_reporting_workflow(self, full_sensor_setup):
        """Test error code reporting."""
        sensor = full_sensor_setup

        # No error
        sensor.updateInfo("0", "shellies/flood-1/error")
        assert sensor.setDriver.call_args_list[0] == (("GPV", "0"),)

        sensor.setDriver.reset_mock()

        # Error occurred
        sensor.updateInfo("1", "shellies/flood-1/error")
        assert sensor.setDriver.call_args_list[0] == (("GPV", "1"),)

    def test_complete_status_update_workflow(self, full_sensor_setup):
        """Test complete status update with all topics."""
        sensor = full_sensor_setup

        # Simulate receiving all sensor data
        updates = [
            ("temperature", "72.0", "CLITEMP"),
            ("flood", "false", "GV0"),
            ("battery", "85", "BATLVL"),
            ("error", "0", "GPV"),
        ]

        for topic, payload, expected_driver in updates:
            sensor.setDriver.reset_mock()
            sensor.updateInfo(payload, f"shellies/sensor/{topic}")

            # Verify correct driver updated and device marked online
            calls = sensor.setDriver.call_args_list
            assert len(calls) == 2
            assert calls[0][0][0] == expected_driver
            assert calls[1] == (("ST", 1),)

    def test_query_workflow(self, full_sensor_setup):
        """Test query workflow."""
        sensor = full_sensor_setup

        # Query current state
        sensor.query(None)

        sensor.reportDrivers.assert_called_once()

    def test_temperature_changes_workflow(self, full_sensor_setup):
        """Test temperature fluctuations."""
        sensor = full_sensor_setup

        temperatures = ["68.5", "70.2", "72.8", "71.0"]

        for temp in temperatures:
            sensor.setDriver.reset_mock()
            sensor.updateInfo(temp, "home/temperature")
            assert sensor.setDriver.call_args_list[0] == (("CLITEMP", temp),)
