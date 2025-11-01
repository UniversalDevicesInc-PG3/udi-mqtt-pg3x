"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2025

node MQShellyFlood

Adding support for the Shelly Flood class of devices. Notably, Shellies publish
their statuses on multiple single-value topics, rather than a single topic
with a JSON object for the status. You will need to pass an array for the
status_topic value in the JSON definition; see the POLYGLOT_CONFIG.md for
details.
"""

# std libraries
pass

# external libraries
from udi_interface import Node, LOGGER

# personal libraries
pass

# Constants
TOPIC_MAP = {
    "temperature": "CLITEMP",
    "flood": "GV0",
    "battery": "BATLVL",
    "error": "GPV",
}


class MQShellyFlood(Node):
    """Node representing a Shelly Flood sensor."""
    id = 'mqshflood'

    def __init__(self, polyglot, primary, address, name, device):
        """Initializes the MQShellyFlood node.

        Args:
            polyglot: Reference to the Polyglot interface.
            primary: The address of the parent node.
            address: The address of this node.
            name: The name of this node.
            device: Dictionary containing device-specific information.
        """
        super().__init__(polyglot, primary, address, name)
        self.lpfx = f'{address}:{name}'


    def updateInfo(self, payload: str, topic: str):
        """Updates a specific driver based on the topic and payload from MQTT."""
        LOGGER.info(f"{self.lpfx} topic:{topic}, payload:{payload}")

        topic_suffix = topic.split('/')[-1]
        driver = TOPIC_MAP.get(topic_suffix)

        if driver:
            # Special handling for the boolean 'flood' topic
            if driver == "GV0":
                value = 1 if payload.lower() == "true" else 0
            else:
                value = payload
            
            self.setDriver(driver, value)
            self.setDriver("ST", 1)  # Report device is online
        else:
            LOGGER.warning(f"Unable to handle message on unknown topic suffix: {topic_suffix}")
        
        LOGGER.debug(f"{self.lpfx} Exit")


    def query(self, command=None):
        """Handles the 'QUERY' command from ISY.

        This is called by ISY to report all drivers for this node.
        """
        LOGGER.info(f"{self.lpfx} {command}")
        self.reportDrivers()
        LOGGER.debug(f"{self.lpfx} Exit")


    # all the drivers - for reference
    # UOMs of interest:
    # 17 = degrees F (temp)
    # 2 = boolean (flood)
    # 51 = percent (battery)
    # 56 = raw value from device (error)

    # Driver controls of interest:
    # BATLVL = battery level
    # CLITEMP = current temperature
    # GPV = general purpose value
    # GV0 = custom control 0
    drivers = [
        {"driver": "ST", "value": 0, "uom": 2},
        {"driver": "CLITEMP", "value": 0, "uom": 17},  # Temperature sensor
        {"driver": "GV0", "value": 0, "uom": 2},  # flood or not
        {"driver": "BATLVL", "value": 0, "uom": 51},  # battery level indicator
        {"driver": "GPV", "value": 0, "uom": 56},  # error code
    ]


    """
    This is a dictionary of commands. If ISY sends a command to the NodeServer,
    this tells it which method to call. DON calls setOn, etc.
    """
    commands = {
        "QUERY": query,
    }