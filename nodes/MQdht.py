"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2024

node MQdht

This class adds support for temperature/humidity/Dewpoint sensors.
It was originally developed with an AM2301
"""

import udi_interface
import json

LOGGER = udi_interface.LOGGER

class MQdht(udi_interface.Node):
    id = 'mqdht'
    
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
        LOGGER.debug(f'DEVCLASS: {device} ')
        self.cmd_topic = device["cmd_topic"]
        if 'sensor_id' in device:
            self.sensor_id = device['sensor_id']
        else:
            self.sensor_id = 'SINGLE_SENSOR'
            device['sensor_id'] = self.sensor_id
        LOGGER.debug(f'CMD_ID {self.sensor_id}, {self.cmd_topic}')
        self.on = False

    def updateInfo(self, payload, topic: str):
        try:
            data = json.loads(payload)
        except Exception as ex:
            LOGGER.error("Failed to parse MQTT Payload as Json: {} {}".format(ex, payload))
            return False
        LOGGER.debug(f'ZZZ {self.sensor_id}, {data} ')
        if 'StatusSNS' in data:
            data = data['StatusSNS']
        if self.sensor_id in data:
            self.setDriver("ST", 1)
            # self.setDriver("ERR", 0)
            self.setDriver("CLITEMP", data[self.sensor_id]["Temperature"])
            self.setDriver("CLIHUM", data[self.sensor_id]["Humidity"])
            self.setDriver("DEWPT", data[self.sensor_id]["DewPoint"])
        else:
            self.setDriver("ST", 0)
            # self.setDriver("ERR", 1)

    def query(self, command=None):
        """
        Called by ISY to report all drivers for this node. This is done in
        the parent class, so you don't need to override this method unless
        there is a need.
        """
        LOGGER.debug(f'QUERY: {self.sensor_id}')
        query_topic = self.cmd_topic.rsplit('/', 1)[0] + '/Status'
        LOGGER.debug(f'QT: {query_topic}')
        self.controller.mqtt_pub(query_topic, " 10")
        self.reportDrivers()
        
    # all the drivers - for reference
    drivers = [
        {"driver": "ST", "value": 0, "uom": 2, "name": "AM2301 ST"},
        {"driver": "CLITEMP", "value": 0, "uom": 17, "name": "Temperature"},
        {"driver": "CLIHUM", "value": 0, "uom": 22, "name": "Humidity"},
        {"driver": "DEWPT", "value": 0, "uom": 17, "name": "Dew Point"},
        # {"driver": "ERR", "value": 0, "uom": 2}
    ]

    """
    This is a dictionary of commands. If ISY sends a command to the NodeServer,
    this tells it which method to call. DON calls setOn, etc.
    """
    commands = {
        "QUERY": query,
    }

