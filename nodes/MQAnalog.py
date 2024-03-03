"""
mqtt-poly NodeServer/Plugin for EISY/Polisy

(C) 2024

node MQAnalog

General purpose Analog input using ADC.
"""

import udi_interface

LOGGER = udi_interface.LOGGER

class MQAnalog(udi_interface.Node):
    id = "mqanal"
    
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
        LOGGER.debug(f'XXX {self.sensor_id}, {data} ')
        if 'StatusSNS' in data:
            data = data['StatusSNS']
        if "ANALOG" in data:
            self.setDriver("ST", 1)
            LOGGER.debug(f'sensor_id UpdateInfo: {self.sensor_id}')
            if self.sensor_id is not 'SINGLE_SENSOR':
                self.setDriver("GPV", data["ANALOG"][self.sensor_id])
                LOGGER.info(f'M-analog {self.sensor_id}:  {data["ANALOG"][self.sensor_id]}')
            else:
                for key, value in data['ANALOG'].items():  # look for the ONLY reading inside 'ANALOG'
                    LOGGER.info(f'single analog {key}: {value}')
                    self.setDriver("GPV", value)
        else:
            LOGGER.debug(f'NOANALOG: {self.sensor_id}')
            self.setDriver("ST", 0)
            self.setDriver("GPV", 0)


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
    # GPV = "General Purpose Value"
    # UOM:56 = "The raw value reported by device"
    drivers = [
        {"driver": "ST", "value": 0, "uom": 2, "name": "Analog ST"},
        {"driver": "GPV", "value": 0, "uom": 56, "name": "Analog"}
    ]

    """
    This is a dictionary of commands. If ISY sends a command to the NodeServer,
    this tells it which method to call. DON calls setOn, etc.
    """
    commands = {
        "QUERY": query,
    }

