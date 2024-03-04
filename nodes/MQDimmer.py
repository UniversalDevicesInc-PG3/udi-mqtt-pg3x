"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2024

node MQDimmer

# Class for a single channel Dimmer. 
# Currently, supports RJWF-02A
"""

import udi_interface
import json

LOGGER = udi_interface.LOGGER

class MQDimmer(udi_interface.Node):
    id = 'mqdimmer'
    
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
        self.status_topic = device['status_topic']
        self.dimmer = 0

    def updateInfo(self, payload, topic: str):
        power = ''
        dimmer = ''
        try:
            data = json.loads(payload)
            if 'Dimmer' in data:
                dimmer = int(data['Dimmer'])
            else:
                dimmer = self.dimmer
            if 'POWER' in data:
                power = data['POWER']
            LOGGER.info("Dimmer = {} , Power = {}".format(dimmer, power))
        except Exception as ex:
            LOGGER.error(f"Could not decode payload {payload}: {ex}")
            return False
        if power == 'ON' or (self.dimmer == 0 and dimmer > 0):
            self.reportCmd("DON")
            self.dimmer = dimmer
            self.setDriver('ST', self.dimmer)
        if power == 'OFF' or (self.dimmer > 0 and dimmer == 0):
            self.reportCmd("DOF")
            self.setDriver('ST', 0)

    def set_on(self, command):
        try:
            if command.get('value') is not None:
                self.dimmer = int(command.get('value'))
        except Exception as ex:
            LOGGER.error(f"Unexpected Dim-Value {ex}, turning to 10%")
            self.dimmer = 10
        if self.dimmer == 0:
            self.dimmer = 10
        self.setDriver('ST', self.dimmer)
        self.controller.mqtt_pub(self.cmd_topic, self.dimmer)

    def set_off(self, command):
        self.controller.mqtt_pub(self.cmd_topic, 0)
        self.setDriver('ST', self.dimmer)

    def brighten(self, command):
        if self.dimmer <= 90:
            self.dimmer += 10
        else:
            self.dimmer = 100
        self.controller.mqtt_pub(self.cmd_topic, self.dimmer)
        self.setDriver('ST', self.dimmer)

    def dim(self, command):
        if self.dimmer >= 10:
            self.dimmer -= 10
        else:
            self.dimmer = 0
        self.controller.mqtt_pub(self.cmd_topic, self.dimmer)
        self.setDriver('ST', self.dimmer)

    def query(self, command=None):
        """
        Called by ISY to report all drivers for this node. This is done in
        the parent class, so you don't need to override this method unless
        there is a need.
        """
        query_topic = self.cmd_topic.rsplit('/', 1)[0] + '/State'
        self.controller.mqtt_pub(query_topic, "")
        LOGGER.info("STATUS_TOPIC = {}".format(self.status_topic))
        self.reportDrivers()
        
    # all the drivers - for reference
    drivers = [
        {'driver': 'ST', 'value': 0, 'uom': 51, 'name': 'Status'}
        ]

    """
    This is a dictionary of commands. If ISY sends a command to the NodeServer,
    this tells it which method to call. DON calls setOn, etc.
    """
    commands = {
        "QUERY": query,
        "DON": set_on,
        "DOF": set_off,
        "BRT": brighten,
        "DIM": dim
    }

    hint = [1, 2, 9, 0]
