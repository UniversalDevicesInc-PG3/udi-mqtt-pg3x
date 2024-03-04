"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2024

node MQShellyFlood

# Adding support for the Shelly Flood class of devices. Notably, Shellies publish their statuses on multiple
# single-value topics, rather than a single topic with a JSON object for the status. You will need to pass
# an array for the status_topic value in the JSON definition; see the POLYGLOT_CONFIG.md for details.
"""

import udi_interface

LOGGER = udi_interface.LOGGER

class MQShellyFlood(udi_interface.Node):
    id = 'mqshflood'
    
    """
    This is the class that all the Nodes will be represented by. You will
    add this to Polyglot/ISY with the interface.addNode method.
    """
    def __init__(self, polyglot, primary, address, name, device):
        """
        Super runs all the parent class necessities.
        :param polyglot: Reference to the Interface class
        :param primary: Parent address
        :param address: This nodes address
        :param name: This nodes name
        """
        super().__init__(polyglot, primary, address, name)
        self.on = False
        self.device = device

    def updateInfo(self, payload, topic: str):
        LOGGER.debug(f"Attempting to handle message for Shelly on topic {topic} with payload {payload}")
        topic_suffix = topic.split('/')[-1]
        self.setDriver("ST", 1)
        if topic_suffix == "temperature":
            self.setDriver("CLITEMP", payload)
        elif topic_suffix == "flood":
            value = payload == "true"
            self.setDriver("GV0", value)
        elif topic_suffix == "battery":
            self.setDriver("BATLVL", payload)
        elif topic_suffix == "error":
            self.setDriver("GPV", payload)
        else:
            LOGGER.warn(f"Unable to handle data for topic {topic}")

    def query(self, command=None):
        """
        Called by ISY to report all drivers for this node. This is done in
        the parent class, so you don't need to override this method unless
        there is a need.
        """
        self.reportDrivers()
        
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

