"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2025

node MQDroplet

This class adds support for Droplet flow / volume sensors.

MQTT Configuration Example:
---------------------------
In your devices configuration, add a Droplet device with the base topic:

  - id: droplet_kitchen
    type: droplet
    status_topic: droplet-ABCD

Where ABCD is your Droplet's 4-character identifier.

The NodeServer will automatically subscribe to:
  - droplet-ABCD/state - JSON with server, signal, flow, volume data
  - droplet-ABCD/health - Plain text "online" or "offline" status

Example state message:
{
    "server": "Connected",
    "signal": "Strong Signal",
    "flow": 0.1,
    "volume": 0.2
}

Note: Droplet devices publish state periodically and do not respond to
command topics.
"""

# std libraries
import json

# external libraries
from udi_interface import Node, LOGGER

# personal libraries
pass


class MQDroplet(Node):
    """Node representing a Droplet flow and volume sensor."""

    id = "mqdroplet"

    def __init__(self, polyglot, primary, address, name, device):
        """Initializes the MQDroplet node.

        Args:
            polyglot: Reference to the Polyglot interface.
            primary: The address of the parent node.
            address: The address of this node.
            name: The name of this node.
            device: Dictionary containing device-specific information.
        """
        super().__init__(polyglot, primary, address, name)
        self.controller = self.poly.getNode(self.primary)
        self.lpfx = f"{address}:{name}"

    def updateInfo(self, payload: str, topic: str):
        """Updates sensor values based on MQTT messages.

        Handles two types of messages:
        1. State topic (JSON): server, signal, flow, volume data
        2. Health topic (text): "online" or "offline" status
        """
        LOGGER.info(f"{self.lpfx} topic:{topic}, payload:{payload}")

        # Handle health topic (plain text)
        if topic.endswith("/health"):
            self._update_health_status(payload)
            return

        # Handle state topic (JSON)
        if topic.endswith("/state"):
            self._update_state_data(payload)
            return

        # Legacy support: if no suffix, assume it's state data
        LOGGER.warning(
            f"{self.lpfx} Topic has no /state or /health suffix, assuming state"
        )
        self._update_state_data(payload)

    def _update_health_status(self, payload: str):
        """Update health status from MQTT LWT message.

        Args:
            payload: Plain text "online" or "offline"
        """
        health_map = {"online": 1, "offline": 0}
        health_value = health_map.get(payload.strip().lower(), 0)
        self.setDriver("GV1", health_value)
        LOGGER.info(f"{self.lpfx} Health status: {payload.strip()} -> {health_value}")

    def _update_state_data(self, payload: str):
        """Update state data from JSON payload.

        Expected payload format:
        {
            "server": "Connected",
            "signal": "Strong Signal",
            "flow": 0.1,
            "volume": 0.2
        }
        """
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as e:
            LOGGER.error(f"Could not decode JSON payload '{payload}': {e}")
            return

        # Map server connectivity status to index
        server_map = {"Connected": 0, "Connecting": 1, "Disconnected": 2}

        # Map signal quality to index
        signal_map = {
            "Initializing": 0,
            "No Signal": 1,
            "Weak Signal": 2,
            "Strong Signal": 3,
        }

        # Update drivers with data from payload
        server_status = data.get("server", "")
        signal_status = data.get("signal", "")

        server_index = server_map.get(server_status, 2)
        self.setDriver("ST", server_index)
        self.setDriver("GV0", signal_map.get(signal_status, 1))

        # Report DON when connected, DOF when disconnected or connecting
        if server_index == 0:  # Connected
            self.reportCmd("DON")
        else:  # Connecting (1) or Disconnected (2)
            self.reportCmd("DOF")

        # Volume is in mL from device, convert to L
        volume_ml = data.get("volume", 0)
        if volume_ml is not None:
            self.setDriver("WVOL", float(volume_ml) / 1000.0)

        # Flow is in L/min from device, convert to L/h for UOM 130
        flow_lpm = data.get("flow", 0)
        if flow_lpm is not None:
            self.setDriver("WATERF", float(flow_lpm) * 60)

        LOGGER.debug(f"{self.lpfx} Exit")

    def query(self, command=None):
        """Handles the 'QUERY' command from ISY.

        Reports current driver values without requesting new data from device.
        Droplet devices publish state periodically and don't respond to queries.
        """
        LOGGER.info(f"{self.lpfx} {command}")
        self.reportDrivers()
        LOGGER.debug(f"{self.lpfx} Exit")

    """
    UOMs:
    2 = boolean
    25 = index
    35 = liter (L)
    130 = Liters per hour (L/h)

    Note: Flow rate from Droplet is in L/min, so we multiply by 60 to convert to L/h

    Driver controls:
    ST: Server Connectivity Status (index: 0=Connected, 1=Connecting, 2=Disconnected)
    GV0: Signal Quality (index: 0=Initializing, 1=No Signal, 2=Weak Signal, 3=Strong Signal)
    GV1: Health Status (boolean: 0=Offline, 1=Online) - MQTT connection via LWT
    WVOL: Water Volume (liters) - point-to-point volume since last update
    WATERF: Water Flow Rate (L/h)
    """
    drivers = [
        {"driver": "ST", "value": 2, "uom": 25, "name": "Server Status"},
        {"driver": "GV0", "value": 1, "uom": 25, "name": "Signal Quality"},
        {"driver": "GV1", "value": 0, "uom": 2, "name": "Health Status"},
        {"driver": "WVOL", "value": 0, "uom": 35, "name": "Volume"},
        {"driver": "WATERF", "value": 0, "uom": 130, "name": "Flow Rate"},
    ]

    """
    Commands that this node can handle.
    Should match the 'accepts' section of the nodedef file.
    Below are receiving commands.
    DON / DOF will be sending commands
    """
    commands = {
        "QUERY": query,
    }
