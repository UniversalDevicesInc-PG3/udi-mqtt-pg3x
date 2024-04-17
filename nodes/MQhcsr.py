"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2024

node MQhcsr

# This class is an attempt to add support for HC-SR04 Ultrasonic Sensor.
# Returns distance in centimeters.
"""

import udi_interface
import json

LOGGER = udi_interface.LOGGER

class MQhcsr(udi_interface.Node):
    id = 'mqhcsr'
    
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

    def updateInfo(self, payload, topic: str):
        try:
            data = json.loads(payload)
        except Exception as ex:
            LOGGER.error(
                "Failed to parse MQTT Payload as Json: {} {}".format(ex, payload)
            )
            return False
        if "SR04" in data:
            self.setDriver("ST", 1)
            self.setDriver("DISTANC", data["SR04"]["Distance"])
        else:
            self.setDriver("ST", 0)
            self.setDriver("DISTANC", 0)

    def query(self, command=None):
        """
        Called by ISY to report all drivers for this node. This is done in
        the parent class, so you don't need to override this method unless
        there is a need.
        """
        self.reportDrivers()
        
    # all the drivers - for reference
    drivers = [
        {"driver": "ST", "value": 0, "uom": 2},
        {"driver": "DISTANC", "value": 0, "uom": 5},
    ]

    """
    This is a dictionary of commands. If ISY sends a command to the NodeServer,
    this tells it which method to call. DON calls setOn, etc.
    """
    commands = {
        "QUERY": query,
    }

