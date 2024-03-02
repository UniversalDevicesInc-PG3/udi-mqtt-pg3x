"""
udi-framework-pg3 NodeServer/Plugin for EISY/PolISY

(C) 2024

nodeFramework
"""

import udi_interface

LOGGER = udi_interface.LOGGER

class Shade(udi_interface.Node):
    id = 'node'
    
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
    def __init__(self, polyglot, primary, address, name, sid):
        """
        Optional.
        Super runs all the parent class necessities. You do NOT have
        to override the __init__ method, but if you do, you MUST call super.

        :param polyglot: Reference to the Interface class
        :param primary: Parent address
        :param address: This nodes address
        :param name: This nodes name
        """
        super(Shade, self).__init__(polyglot, primary, address, name)
        self.poly = polyglot
        self.primary = primary
        self.controller = polyglot.getNode(self.primary)
        self.address = address
        self.name = name


        # Subscribe to various events from the Interface class.
        #
        # The START event is unique in that you can subscribe to 
        # the start event for each node you define.
        self.poly.subscribe(self.poly.START, self.start, address)
        self.poly.subscribe(self.poly.POLL, self.poll)
        
    def start(self):
        """
        This method is called after Polyglot has added the node per the
        START event subscription above
        """
        self.setDriver('GV0', 1)
        # self.updateData()
        self.reportDrivers()

    def poll(self, flag):
        if 'longPoll' in flag:
            LOGGER.debug('longPoll (shade)')
        else:
            LOGGER.debug('shortPoll (shade)')
                   
    def updateData(self):
        pass
        # if self.controller.no_update == False:
        #     LOGGER.debug(self.controller.shades_array)
        #     self.shadedata = list(filter(lambda shade: shade['id'] == self.sid, self.controller.shades_array))
        #     LOGGER.debug(f"shade {self.sid} is {self.shadedata}")
        #     if self.shadedata:
        #         self.shadedata = self.shadedata[0]
        #         self.setDriver('GV1', self.shadedata["roomId"])
        #         self.setDriver('GV6', self.shadedata["batteryStatus"])
        #         self.setDriver('GV5', self.shadedata["capabilities"])
        #         self.positions = self.shadedata["positions"]
        #         self.capabilities = int(self.shadedata["capabilities"])
        #         self.updatePositions(self.positions, self.capabilities)
        #         return True
        # else:
        #     return False

    def query(self, command=None):
        """
        Called by ISY to report all drivers for this node. This is done in
        the parent class, so you don't need to override this method unless
        there is a need.
        """
        self.updateData()
        self.reportDrivers()

        # all the drivers - for reference
    drivers = [
        {'driver': 'ST', 'value': 0, 'uom': 2},
        ]
        # {'driver': 'GV0', 'value': 0, 'uom': 107},
        # {'driver': 'GV1', 'value': 0, 'uom': 107},
        # {'driver': 'GV2', 'value': None, 'uom': 100},
        # {'driver': 'GV3', 'value': None, 'uom': 100},
        # {'driver': 'GV4', 'value': None, 'uom': 100},
        # {'driver': 'GV5', 'value': 0, 'uom': 25},
        # {'driver': 'GV6', 'value': 0, 'uom': 25},
        # ]

    """
    This is a dictionary of commands. If ISY sends a command to the NodeServer,
    this tells it which method to call. DON calls setOn, etc.
    """
    commands = {
    'QUERY': query,
    }
                   
