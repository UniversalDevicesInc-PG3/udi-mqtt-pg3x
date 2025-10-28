"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2024

node MQswitch
"""

import udi_interface

LOGGER = udi_interface.LOGGER


class MQSwitch(udi_interface.Node):
    id = 'MQSW'

    """
    This is the class that all the Nodes will be represented by. You will
    add this to Polyglot/ISY with the interface.addNode method.

    Class Variables:
    self.primary: String address of the parent node.
    self.address: String address of this Node 14 character limit.
                  (ISY limitation)
    self.added: Boolean Confirmed added to ISY

    Class Methods:
    setDriver('ST', 1, report = True, force = False):
        This sets the driver 'ST' to 1. If report is False we do not report
        it to Polyglot/ISY. If force is True, we send a report even if the
        value hasn't changed.
    reportDriver(driver, force): report the driver value to Polyglot/ISY if
        it has changed.  if force is true, send regardless.
    reportDrivers(): Forces a full update of all drivers to Polyglot/ISY.
    query(): Called when ISY sends a query request to Polyglot for this
        specific node
    """

    def __init__(self, polyglot, primary, address, name, device):
        """
        Optional.
        Super runs all the parent class necessities. You do NOT have
        to override the __init__ method, but if you do, you MUST call super.

        :param polyglot: Reference to the Interface class
        :param primary: Parent address
        :param address: This nodes address
        :param name: This nodes name
        """
        super().__init__(polyglot, primary, address, name)
        self.controller = self.poly.getNode(self.primary)
        self.cmd_topic = device["cmd_topic"]
        self.on = False
        

    def updateInfo(self, payload, topic: str):
        if payload == "ON":
            if not self.on:
                self.reportCmd("DON")
                self.on = True
            self.setDriver("ST", 100)
        elif payload == "OFF":
            if self.on:
                self.reportCmd("DOF")
                self.on = False
            self.setDriver("ST", 0)
        else:
            LOGGER.error(f"Topic:{topic}, Invalid payload:{payload}")
            return
        LOGGER.info(f"Topic{topic}, Successful payload:{payload}")
        

    def cmd_on(self, command):
        LOGGER.debug(command)
        self.on = True
        self.controller.mqtt_pub(self.cmd_topic, "ON")
        

    def cmd_off(self, command):
        LOGGER.debug(command)
        self.on = False
        self.controller.mqtt_pub(self.cmd_topic, "OFF")
        

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
        {"driver": "ST", "value": 0, "uom": 78, "name": "Power"}
    ]

    """
    This is a dictionary of commands. If ISY sends a command to the NodeServer,
    this tells it which method to call. DON calls setOn, etc.
    """
    commands = {
        "QUERY": query,
        "DON": cmd_on,
        "DOF": cmd_off}

    hint = [4, 2, 0, 0]
