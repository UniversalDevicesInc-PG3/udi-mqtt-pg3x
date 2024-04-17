"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2024

node MQraw

"""

import udi_interface

LOGGER = udi_interface.LOGGER

class MQraw(udi_interface.Node):
    id = 'mqr'
    
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
        self.cmd_topic = device["cmd_topic"]
        self.on = False

    def updateInfo(self, payload, topic: str):
        try:
            self.setDriver("ST", 1)
            self.setDriver("GV1", int(payload))
        except Exception as ex:
            LOGGER.error("Failed to parse MQTT Payload: {} {}".format(ex, payload))

    def query(self, command=None):
        """
        Called by ISY to report all drivers for this node. This is done in
        the parent class, so you don't need to override this method unless
        there is a need.
        """
        self.reportDrivers()
        
    drivers = [
        {"driver": "ST", "value": 0, "uom": 2},
        {"driver": "GV1", "value": 0, "uom": 56},
    ]

    """
    This is a dictionary of commands. If ISY sends a command to the NodeServer,
    this tells it which method to call. DON calls setOn, etc.
    """
    commands = {
        "QUERY": query,
    }

