"""
mqtt-poly NodeServer/Plugin for EISY/Polisy

(C) 2024

node MQFlag

this meant as a flag for if you have a sensor or condition on your IOT device
which you want the device program rather than the ISY to flag
FLAG-0 = OK
FLAG-1 = NOK
FLAG-2 = LO
FLAG-3 = HI
FLAG-4 = ERR
FLAG-5 = IN
FLAG-6 = OUT
FLAG-7 = UP
FLAG-8 = DOWN
FLAG-9 = TRIGGER
FLAG-10 = ON
FLAG-11 = OFF
FLAG-12 = ---
payload is direct (like SW) not JSON encoded (like SENSOR)
example device: liquid float {OK, LO, HI}
example condition: IOT devices sensor connections {OK, NOK, ERR(OR)}
"""

import udi_interface

LOGGER = udi_interface.LOGGER

class MQFlag(udi_interface.Node):
    id = "mqflag"
    
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
        self.controller = self.poly.getNode(self.primary)
        self.cmd_topic = device["cmd_topic"]

    def updateInfo(self, payload, topic: str):
        if payload == "OK":
            self.setDriver("ST", 0)
        elif payload == "NOK":
            self.setDriver("ST", 1)
        elif payload == "LO":
            self.setDriver("ST", 2)
        elif payload == "HI":
            self.setDriver("ST", 3)
        elif payload == "IN":
            self.setDriver("ST", 5)
        elif payload == "OUT":
            self.setDriver("ST", 6)
        elif payload == "UP":
            self.setDriver("ST", 7)
        elif payload == "DOWN":
            self.setDriver("ST", 8)
        elif payload == "TRIGGER":
            self.setDriver("ST", 9)
        elif payload == "ON":
            self.setDriver("ST", 10)
        elif payload == "OFF":
            self.setDriver("ST", 11)
        elif payload == "---":
            self.setDriver("ST", 12)
        else:
            LOGGER.error("Invalid payload {}".format(payload))
            payload = "ERR"
            self.setDriver("ST", 4)

    def reset_send(self, command):
        self.controller.mqtt_pub(self.cmd_topic, "RESET")

    def query(self, command=None):
        """
        Called by ISY to report all drivers for this node. This is done in
        the parent class, so you don't need to override this method unless
        there is a need.
        """
        self.controller.mqtt_pub(self.cmd_topic, "")
        self.reportDrivers()

    # all the drivers - for reference
    drivers = [
        {"driver": "ST", "value": 0, "uom": 25}
    ]

    """
    This is a dictionary of commands. If ISY sends a command to the NodeServer,
    this tells it which method to call. DON calls setOn, etc.
    """
    commands = {
        "QUERY": query,
        "RESET": reset_send
    }

