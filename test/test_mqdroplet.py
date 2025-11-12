"""
Comprehensive test suite for MQDroplet node.

Tests cover:
- Initialization
- Health topic handling (plain text online/offline)
- State topic handling (JSON with server, signal, flow, volume)
- Unit conversions (mL to L, L/min to L/h)
- Server status mapping and DON/DOF commands
- Signal quality mapping
- Query command
- Topic routing based on suffix
- Edge cases and error handling
"""

import json
import pytest
from unittest.mock import Mock
from nodes.MQDroplet import MQDroplet


class TestMQDropletInitialization:
    """Tests for MQDroplet initialization."""

    @pytest.fixture
    def mock_polyglot(self):
        """Create a mock polyglot interface."""
        poly = Mock()
        poly.getNode = Mock(return_value=Mock())
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        return poly

    @pytest.fixture
    def device_config(self):
        """Create a sample device configuration."""
        return {"status_topic": "droplet-ABCD"}

    def test_initialization_basic(self, mock_polyglot, device_config):
        """Test basic MQDroplet initialization."""
        droplet = MQDroplet(
            mock_polyglot, "controller", "droplet_1", "Kitchen Droplet", device_config
        )

        assert droplet.id == "mqdroplet"
        assert droplet.address == "droplet_1"
        assert droplet.name == "Kitchen Droplet"
        assert droplet.lpfx == "droplet_1:Kitchen Droplet"

    def test_initialization_different_identifier(self, mock_polyglot):
        """Test initialization with different identifier."""
        device = {"status_topic": "droplet-XY12"}
        droplet = MQDroplet(
            mock_polyglot, "controller", "bathroom", "Bathroom Sensor", device
        )

        assert droplet.lpfx == "bathroom:Bathroom Sensor"


class TestMQDropletHealthStatus:
    """Tests for health status updates (LWT)."""

    @pytest.fixture
    def droplet_node(self):
        """Create a MQDroplet instance for testing."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        poly.getNode = Mock(return_value=Mock())

        device = {"status_topic": "droplet-ABCD"}
        node = MQDroplet(poly, "controller", "droplet", "Test", device)
        node.setDriver = Mock()

        return node

    def test_health_status_online(self, droplet_node):
        """Test health status update with 'online'."""
        payload = "online"

        droplet_node.updateInfo(payload, "droplet-ABCD/health")

        droplet_node.setDriver.assert_called_once_with("GV1", 1)

    def test_health_status_offline(self, droplet_node):
        """Test health status update with 'offline'."""
        payload = "offline"

        droplet_node.updateInfo(payload, "droplet-ABCD/health")

        droplet_node.setDriver.assert_called_once_with("GV1", 0)

    def test_health_status_online_uppercase(self, droplet_node):
        """Test health status with uppercase 'ONLINE'."""
        payload = "ONLINE"

        droplet_node.updateInfo(payload, "droplet-ABCD/health")

        droplet_node.setDriver.assert_called_once_with("GV1", 1)

    def test_health_status_offline_mixed_case(self, droplet_node):
        """Test health status with mixed case 'OffLine'."""
        payload = "OffLine"

        droplet_node.updateInfo(payload, "droplet-ABCD/health")

        droplet_node.setDriver.assert_called_once_with("GV1", 0)

    def test_health_status_with_whitespace(self, droplet_node):
        """Test health status with leading/trailing whitespace."""
        payload = "  online  "

        droplet_node.updateInfo(payload, "droplet-ABCD/health")

        droplet_node.setDriver.assert_called_once_with("GV1", 1)

    def test_health_status_unknown_value(self, droplet_node):
        """Test health status with unknown value defaults to offline."""
        payload = "unknown"

        droplet_node.updateInfo(payload, "droplet-ABCD/health")

        droplet_node.setDriver.assert_called_once_with("GV1", 0)

    def test_health_status_empty_string(self, droplet_node):
        """Test health status with empty string defaults to offline."""
        payload = ""

        droplet_node.updateInfo(payload, "droplet-ABCD/health")

        droplet_node.setDriver.assert_called_once_with("GV1", 0)


class TestMQDropletStateData:
    """Tests for state data updates (JSON)."""

    @pytest.fixture
    def droplet_node(self):
        """Create a MQDroplet instance for testing."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        poly.getNode = Mock(return_value=Mock())

        device = {"status_topic": "droplet-ABCD"}
        node = MQDroplet(poly, "controller", "droplet", "Test", device)
        node.setDriver = Mock()
        node.reportCmd = Mock()

        return node

    def test_state_data_complete(self, droplet_node):
        """Test handling complete state data."""
        payload = json.dumps(
            {
                "server": "Connected",
                "signal": "Strong Signal",
                "flow": 2.5,
                "volume": 150,
            }
        )

        droplet_node.updateInfo(payload, "droplet-ABCD/state")

        calls = droplet_node.setDriver.call_args_list
        assert len(calls) == 4
        assert calls[0] == (("ST", 0),)  # Connected = 0
        assert calls[1] == (("GV0", 3),)  # Strong Signal = 3
        assert calls[2] == (("WVOL", 0.15),)  # 150 mL = 0.15 L
        assert calls[3] == (("WATERF", 150.0),)  # 2.5 L/min = 150 L/h

        droplet_node.reportCmd.assert_called_once_with("DON")

    def test_state_data_server_connecting(self, droplet_node):
        """Test server status 'Connecting'."""
        payload = json.dumps(
            {"server": "Connecting", "signal": "Weak Signal", "flow": 0.0, "volume": 0}
        )

        droplet_node.updateInfo(payload, "droplet-ABCD/state")

        calls = droplet_node.setDriver.call_args_list
        assert calls[0] == (("ST", 1),)  # Connecting = 1
        assert calls[1] == (("GV0", 2),)  # Weak Signal = 2

        droplet_node.reportCmd.assert_called_once_with("DOF")

    def test_state_data_server_disconnected(self, droplet_node):
        """Test server status 'Disconnected'."""
        payload = json.dumps(
            {"server": "Disconnected", "signal": "No Signal", "flow": 0.0, "volume": 0}
        )

        droplet_node.updateInfo(payload, "droplet-ABCD/state")

        calls = droplet_node.setDriver.call_args_list
        assert calls[0] == (("ST", 2),)  # Disconnected = 2
        assert calls[1] == (("GV0", 1),)  # No Signal = 1

        droplet_node.reportCmd.assert_called_once_with("DOF")

    def test_state_data_signal_initializing(self, droplet_node):
        """Test signal quality 'Initializing'."""
        payload = json.dumps(
            {"server": "Connected", "signal": "Initializing", "flow": 0.0, "volume": 0}
        )

        droplet_node.updateInfo(payload, "droplet-ABCD/state")

        calls = droplet_node.setDriver.call_args_list
        assert calls[1] == (("GV0", 0),)  # Initializing = 0

    def test_state_data_volume_conversion(self, droplet_node):
        """Test volume conversion from mL to L."""
        payload = json.dumps(
            {
                "server": "Connected",
                "signal": "Strong Signal",
                "flow": 1.0,
                "volume": 500,
            }
        )

        droplet_node.updateInfo(payload, "droplet-ABCD/state")

        calls = droplet_node.setDriver.call_args_list
        assert calls[2] == (("WVOL", 0.5),)  # 500 mL = 0.5 L

    def test_state_data_flow_conversion(self, droplet_node):
        """Test flow conversion from L/min to L/h."""
        payload = json.dumps(
            {
                "server": "Connected",
                "signal": "Strong Signal",
                "flow": 3.5,
                "volume": 100,
            }
        )

        droplet_node.updateInfo(payload, "droplet-ABCD/state")

        calls = droplet_node.setDriver.call_args_list
        assert calls[3] == (("WATERF", 210.0),)  # 3.5 L/min * 60 = 210 L/h

    def test_state_data_zero_values(self, droplet_node):
        """Test handling zero flow and volume."""
        payload = json.dumps(
            {"server": "Connected", "signal": "Strong Signal", "flow": 0.0, "volume": 0}
        )

        droplet_node.updateInfo(payload, "droplet-ABCD/state")

        calls = droplet_node.setDriver.call_args_list
        assert calls[2] == (("WVOL", 0.0),)
        assert calls[3] == (("WATERF", 0.0),)

    def test_state_data_high_flow_rate(self, droplet_node):
        """Test handling high flow rate."""
        payload = json.dumps(
            {
                "server": "Connected",
                "signal": "Strong Signal",
                "flow": 15.0,
                "volume": 5000,
            }
        )

        droplet_node.updateInfo(payload, "droplet-ABCD/state")

        calls = droplet_node.setDriver.call_args_list
        assert calls[2] == (("WVOL", 5.0),)  # 5000 mL = 5 L
        assert calls[3] == (("WATERF", 900.0),)  # 15 L/min * 60 = 900 L/h

    def test_state_data_small_volume(self, droplet_node):
        """Test handling small volume (decimal precision)."""
        payload = json.dumps(
            {
                "server": "Connected",
                "signal": "Strong Signal",
                "flow": 0.1,
                "volume": 0.2,
            }
        )

        droplet_node.updateInfo(payload, "droplet-ABCD/state")

        calls = droplet_node.setDriver.call_args_list
        assert calls[2] == (("WVOL", 0.0002),)  # 0.2 mL = 0.0002 L
        assert calls[3] == (("WATERF", 6.0),)  # 0.1 L/min * 60 = 6 L/h

    def test_state_data_missing_server_field(self, droplet_node):
        """Test handling missing server field."""
        payload = json.dumps({"signal": "Strong Signal", "flow": 1.0, "volume": 100})

        droplet_node.updateInfo(payload, "droplet-ABCD/state")

        calls = droplet_node.setDriver.call_args_list
        assert calls[0] == (("ST", 2),)  # Default to Disconnected

    def test_state_data_missing_signal_field(self, droplet_node):
        """Test handling missing signal field."""
        payload = json.dumps({"server": "Connected", "flow": 1.0, "volume": 100})

        droplet_node.updateInfo(payload, "droplet-ABCD/state")

        calls = droplet_node.setDriver.call_args_list
        assert calls[1] == (("GV0", 1),)  # Default to No Signal

    def test_state_data_missing_flow_field(self, droplet_node):
        """Test handling missing flow field."""
        payload = json.dumps(
            {"server": "Connected", "signal": "Strong Signal", "volume": 100}
        )

        droplet_node.updateInfo(payload, "droplet-ABCD/state")

        calls = droplet_node.setDriver.call_args_list
        assert calls[3] == (("WATERF", 0.0),)  # Default to 0

    def test_state_data_missing_volume_field(self, droplet_node):
        """Test handling missing volume field."""
        payload = json.dumps(
            {"server": "Connected", "signal": "Strong Signal", "flow": 1.0}
        )

        droplet_node.updateInfo(payload, "droplet-ABCD/state")

        calls = droplet_node.setDriver.call_args_list
        assert calls[2] == (("WVOL", 0.0),)  # Default to 0

    def test_state_data_unknown_server_status(self, droplet_node):
        """Test handling unknown server status."""
        payload = json.dumps(
            {"server": "Unknown", "signal": "Strong Signal", "flow": 1.0, "volume": 100}
        )

        droplet_node.updateInfo(payload, "droplet-ABCD/state")

        calls = droplet_node.setDriver.call_args_list
        assert calls[0] == (("ST", 2),)  # Default to Disconnected

        droplet_node.reportCmd.assert_called_once_with("DOF")

    def test_state_data_unknown_signal_quality(self, droplet_node):
        """Test handling unknown signal quality."""
        payload = json.dumps(
            {"server": "Connected", "signal": "Unknown", "flow": 1.0, "volume": 100}
        )

        droplet_node.updateInfo(payload, "droplet-ABCD/state")

        calls = droplet_node.setDriver.call_args_list
        assert calls[1] == (("GV0", 1),)  # Default to No Signal

    def test_state_data_invalid_json(self, droplet_node):
        """Test handling invalid JSON payload."""
        payload = "not valid json {"

        droplet_node.updateInfo(payload, "droplet-ABCD/state")

        droplet_node.setDriver.assert_not_called()

    def test_state_data_empty_json(self, droplet_node):
        """Test handling empty JSON object."""
        payload = json.dumps({})

        droplet_node.updateInfo(payload, "droplet-ABCD/state")

        calls = droplet_node.setDriver.call_args_list
        # Should use default values
        assert calls[0] == (("ST", 2),)  # Default disconnected
        assert calls[1] == (("GV0", 1),)  # Default no signal

    def test_state_data_extra_fields_ignored(self, droplet_node):
        """Test that extra fields in payload are ignored."""
        payload = json.dumps(
            {
                "server": "Connected",
                "signal": "Strong Signal",
                "flow": 1.0,
                "volume": 100,
                "extra_field": "ignored",
                "temperature": 25,
            }
        )

        droplet_node.updateInfo(payload, "droplet-ABCD/state")

        calls = droplet_node.setDriver.call_args_list
        assert len(calls) == 4  # Only 4 expected drivers


class TestMQDropletTopicRouting:
    """Tests for topic-based message routing."""

    @pytest.fixture
    def droplet_node(self):
        """Create a MQDroplet instance for testing."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        poly.getNode = Mock(return_value=Mock())

        device = {"status_topic": "droplet-ABCD"}
        node = MQDroplet(poly, "controller", "droplet", "Test", device)
        node.setDriver = Mock()
        node.reportCmd = Mock()

        return node

    def test_routing_health_topic(self, droplet_node):
        """Test message routing for /health topic."""
        payload = "online"

        droplet_node.updateInfo(payload, "droplet-ABCD/health")

        # Should only set GV1 (health status)
        droplet_node.setDriver.assert_called_once_with("GV1", 1)
        droplet_node.reportCmd.assert_not_called()

    def test_routing_state_topic(self, droplet_node):
        """Test message routing for /state topic."""
        payload = json.dumps(
            {
                "server": "Connected",
                "signal": "Strong Signal",
                "flow": 1.0,
                "volume": 100,
            }
        )

        droplet_node.updateInfo(payload, "droplet-ABCD/state")

        # Should set ST, GV0, WVOL, WATERF
        calls = droplet_node.setDriver.call_args_list
        assert len(calls) == 4
        droplet_node.reportCmd.assert_called_once()

    def test_routing_legacy_topic_without_suffix(self, droplet_node):
        """Test legacy support for topics without /state or /health suffix."""
        payload = json.dumps(
            {
                "server": "Connected",
                "signal": "Strong Signal",
                "flow": 1.0,
                "volume": 100,
            }
        )

        droplet_node.updateInfo(payload, "droplet-ABCD")

        # Should treat as state data
        calls = droplet_node.setDriver.call_args_list
        assert len(calls) == 4

    def test_routing_nested_health_topic(self, droplet_node):
        """Test routing with nested path ending in /health."""
        payload = "offline"

        droplet_node.updateInfo(payload, "home/sensors/droplet-ABCD/health")

        droplet_node.setDriver.assert_called_once_with("GV1", 0)

    def test_routing_nested_state_topic(self, droplet_node):
        """Test routing with nested path ending in /state."""
        payload = json.dumps(
            {
                "server": "Connected",
                "signal": "Strong Signal",
                "flow": 1.0,
                "volume": 100,
            }
        )

        droplet_node.updateInfo(payload, "home/sensors/droplet-ABCD/state")

        calls = droplet_node.setDriver.call_args_list
        assert len(calls) == 4


class TestMQDropletQuery:
    """Tests for query command."""

    @pytest.fixture
    def droplet_with_report(self):
        """Create a MQDroplet with mocked reportDrivers."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        poly.getNode = Mock(return_value=Mock())

        device = {"status_topic": "droplet-ABCD"}
        node = MQDroplet(poly, "controller", "droplet", "Test", device)
        node.reportDrivers = Mock()

        return node

    def test_query_command(self, droplet_with_report):
        """Test QUERY command."""
        command = {"cmd": "QUERY"}

        droplet_with_report.query(command)

        droplet_with_report.reportDrivers.assert_called_once()

    def test_query_command_none(self, droplet_with_report):
        """Test QUERY command with None parameter."""
        droplet_with_report.query(None)

        droplet_with_report.reportDrivers.assert_called_once()


class TestMQDropletDriversAndCommands:
    """Tests for node configuration."""

    def test_node_id(self):
        """Test node ID is correct."""
        assert MQDroplet.id == "mqdroplet"

    def test_drivers_configuration(self):
        """Test drivers are properly configured."""
        assert len(MQDroplet.drivers) == 5

        driver_dict = {d["driver"]: d for d in MQDroplet.drivers}

        assert driver_dict["ST"]["uom"] == 25  # index
        assert driver_dict["ST"]["value"] == 2  # Default: Disconnected
        assert driver_dict["ST"]["name"] == "Server Status"

        assert driver_dict["GV0"]["uom"] == 25  # index
        assert driver_dict["GV0"]["value"] == 1  # Default: No Signal
        assert driver_dict["GV0"]["name"] == "Signal Quality"

        assert driver_dict["GV1"]["uom"] == 2  # boolean
        assert driver_dict["GV1"]["value"] == 0  # Default: Offline
        assert driver_dict["GV1"]["name"] == "Health Status"

        assert driver_dict["WVOL"]["uom"] == 35  # liters
        assert driver_dict["WVOL"]["name"] == "Volume"

        assert driver_dict["WATERF"]["uom"] == 130  # L/h
        assert driver_dict["WATERF"]["name"] == "Flow Rate"

    def test_commands_configuration(self):
        """Test commands are properly configured."""
        assert "QUERY" in MQDroplet.commands
        assert MQDroplet.commands["QUERY"] == MQDroplet.query


class TestMQDropletIntegration:
    """Integration tests for complete workflows."""

    @pytest.fixture
    def full_setup(self):
        """Create a fully mocked setup."""
        poly = Mock()
        poly.db_getNodeDrivers = Mock(return_value=[])
        poly.subscribe = Mock()
        poly.getNode = Mock(return_value=Mock())

        device = {"status_topic": "droplet-F674"}
        node = MQDroplet(poly, "controller", "kitchen_droplet", "Kitchen Water", device)
        node.setDriver = Mock()
        node.reportCmd = Mock()
        node.reportDrivers = Mock()

        return node

    def test_device_startup_workflow(self, full_setup):
        """Test workflow when device starts up."""
        droplet = full_setup

        # Device comes online
        droplet.updateInfo("online", "droplet-F674/health")
        assert droplet.setDriver.call_args_list[0] == (("GV1", 1),)

        droplet.setDriver.reset_mock()

        # Initial state message
        payload = json.dumps(
            {"server": "Connecting", "signal": "Initializing", "flow": 0.0, "volume": 0}
        )
        droplet.updateInfo(payload, "droplet-F674/state")

        calls = droplet.setDriver.call_args_list
        assert calls[0] == (("ST", 1),)  # Connecting
        assert calls[1] == (("GV0", 0),)  # Initializing
        droplet.reportCmd.assert_called_once_with("DOF")

        droplet.setDriver.reset_mock()
        droplet.reportCmd.reset_mock()

        # Device fully connected
        payload = json.dumps(
            {"server": "Connected", "signal": "Strong Signal", "flow": 0.0, "volume": 0}
        )
        droplet.updateInfo(payload, "droplet-F674/state")

        calls = droplet.setDriver.call_args_list
        assert calls[0] == (("ST", 0),)  # Connected
        assert calls[1] == (("GV0", 3),)  # Strong Signal
        droplet.reportCmd.assert_called_once_with("DON")

    def test_water_flow_monitoring_workflow(self, full_setup):
        """Test continuous water flow monitoring."""
        droplet = full_setup

        # No flow
        payload = json.dumps(
            {"server": "Connected", "signal": "Strong Signal", "flow": 0.0, "volume": 0}
        )
        droplet.updateInfo(payload, "droplet-F674/state")

        calls = droplet.setDriver.call_args_list
        assert calls[2] == (("WVOL", 0.0),)
        assert calls[3] == (("WATERF", 0.0),)

        droplet.setDriver.reset_mock()

        # Flow starts - shower
        payload = json.dumps(
            {
                "server": "Connected",
                "signal": "Strong Signal",
                "flow": 8.5,
                "volume": 2500,
            }
        )
        droplet.updateInfo(payload, "droplet-F674/state")

        calls = droplet.setDriver.call_args_list
        assert calls[2] == (("WVOL", 2.5),)  # 2.5 L
        assert calls[3] == (("WATERF", 510.0),)  # 8.5 L/min * 60 = 510 L/h

        droplet.setDriver.reset_mock()

        # Flow continues
        payload = json.dumps(
            {
                "server": "Connected",
                "signal": "Strong Signal",
                "flow": 8.2,
                "volume": 3200,
            }
        )
        droplet.updateInfo(payload, "droplet-F674/state")

        calls = droplet.setDriver.call_args_list
        assert calls[2] == (("WVOL", 3.2),)  # 3.2 L
        # Use approximate comparison for floating point
        assert abs(calls[3][0][1] - 492.0) < 0.01  # 8.2 L/min * 60 ≈ 492 L/h

    def test_connection_loss_and_recovery_workflow(self, full_setup):
        """Test connection loss and recovery."""
        droplet = full_setup

        # Normal operation
        payload = json.dumps(
            {
                "server": "Connected",
                "signal": "Strong Signal",
                "flow": 1.0,
                "volume": 500,
            }
        )
        droplet.updateInfo(payload, "droplet-F674/state")
        droplet.reportCmd.assert_called_with("DON")

        droplet.setDriver.reset_mock()
        droplet.reportCmd.reset_mock()

        # WiFi drops - device goes offline
        droplet.updateInfo("offline", "droplet-F674/health")
        assert droplet.setDriver.call_args_list[0] == (("GV1", 0),)

        droplet.setDriver.reset_mock()

        # Device reconnects to WiFi
        droplet.updateInfo("online", "droplet-F674/health")
        assert droplet.setDriver.call_args_list[0] == (("GV1", 1),)

        droplet.setDriver.reset_mock()

        # Cloud connection reestablishes
        payload = json.dumps(
            {"server": "Connected", "signal": "Weak Signal", "flow": 0.0, "volume": 0}
        )
        droplet.updateInfo(payload, "droplet-F674/state")

        calls = droplet.setDriver.call_args_list
        assert calls[0] == (("ST", 0),)  # Connected
        assert calls[1] == (("GV0", 2),)  # Weak Signal
        droplet.reportCmd.assert_called_with("DON")

    def test_signal_quality_changes_workflow(self, full_setup):
        """Test signal quality changes during operation."""
        droplet = full_setup

        # Strong signal
        payload = json.dumps(
            {
                "server": "Connected",
                "signal": "Strong Signal",
                "flow": 2.0,
                "volume": 1000,
            }
        )
        droplet.updateInfo(payload, "droplet-F674/state")
        assert droplet.setDriver.call_args_list[1] == (("GV0", 3),)

        droplet.setDriver.reset_mock()

        # Signal degrades
        payload = json.dumps(
            {
                "server": "Connected",
                "signal": "Weak Signal",
                "flow": 2.0,
                "volume": 1000,
            }
        )
        droplet.updateInfo(payload, "droplet-F674/state")
        assert droplet.setDriver.call_args_list[1] == (("GV0", 2),)

        droplet.setDriver.reset_mock()

        # Signal lost
        payload = json.dumps(
            {"server": "Connected", "signal": "No Signal", "flow": 0.0, "volume": 0}
        )
        droplet.updateInfo(payload, "droplet-F674/state")
        assert droplet.setDriver.call_args_list[1] == (("GV0", 1),)

    def test_query_during_operation_workflow(self, full_setup):
        """Test query command during normal operation."""
        droplet = full_setup

        # Set some data
        payload = json.dumps(
            {
                "server": "Connected",
                "signal": "Strong Signal",
                "flow": 5.0,
                "volume": 2000,
            }
        )
        droplet.updateInfo(payload, "droplet-F674/state")

        # Query current state
        droplet.query({"cmd": "QUERY"})

        droplet.reportDrivers.assert_called_once()

    def test_small_leak_detection_workflow(self, full_setup):
        """Test detecting a small continuous leak."""
        droplet = full_setup

        # Small continuous flow (potential leak)
        for _ in range(5):
            payload = json.dumps(
                {
                    "server": "Connected",
                    "signal": "Strong Signal",
                    "flow": 0.05,
                    "volume": 50,
                }
            )
            droplet.updateInfo(payload, "droplet-F674/state")
            droplet.setDriver.reset_mock()

        # Verify last reading
        payload = json.dumps(
            {
                "server": "Connected",
                "signal": "Strong Signal",
                "flow": 0.05,
                "volume": 50,
            }
        )
        droplet.updateInfo(payload, "droplet-F674/state")

        calls = droplet.setDriver.call_args_list
        assert calls[2] == (("WVOL", 0.05),)  # 50 mL = 0.05 L
        assert calls[3] == (("WATERF", 3.0),)  # 0.05 L/min * 60 = 3 L/h

    def test_high_volume_usage_workflow(self, full_setup):
        """Test high volume water usage (filling pool, etc)."""
        droplet = full_setup

        # High flow rate
        payload = json.dumps(
            {
                "server": "Connected",
                "signal": "Strong Signal",
                "flow": 30.0,
                "volume": 15000,
            }
        )
        droplet.updateInfo(payload, "droplet-F674/state")

        calls = droplet.setDriver.call_args_list
        assert calls[2] == (("WVOL", 15.0),)  # 15000 mL = 15 L
        assert calls[3] == (("WATERF", 1800.0),)  # 30 L/min * 60 = 1800 L/h

    def test_server_cloud_issues_workflow(self, full_setup):
        """Test Droplet operating with cloud server issues."""
        droplet = full_setup

        # Device online but cloud disconnected
        droplet.updateInfo("online", "droplet-F674/health")
        assert droplet.setDriver.call_args_list[0] == (("GV1", 1),)

        droplet.setDriver.reset_mock()

        # Cloud server issue
        payload = json.dumps(
            {
                "server": "Disconnected",
                "signal": "Strong Signal",
                "flow": 2.0,
                "volume": 1000,
            }
        )
        droplet.updateInfo(payload, "droplet-F674/state")

        calls = droplet.setDriver.call_args_list
        assert calls[0] == (("ST", 2),)  # Disconnected from cloud
        assert calls[1] == (("GV0", 3),)  # But sensor still working
        droplet.reportCmd.assert_called_with("DOF")

        # Flow data still accurate (local processing)
        assert calls[2] == (("WVOL", 1.0),)
        assert calls[3] == (("WATERF", 120.0),)
