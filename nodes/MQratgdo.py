"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2024

node MQratgdo

Class for Ratgdo Garage door opener for MYQ replacement
Able to control door, light, lock and get status of same as well as motion, obstruction
"""

import udi_interface

LOGGER = udi_interface.LOGGER

class MQratgdo(udi_interface.Node):
    id = 'mqratgdo'
    
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
        self.cmd_topic = device["cmd_topic"] + "/command/"
        self.poly.subscribe(self.poly.POLL, self.poll)
        self.device = device
        self.motion = False

    """
    Called via the POLL event.  The POLL event is triggerd at
    the intervals specified in the node server configuration. There
    are two separate poll events, a long poll and a short poll. Which
    one is indicated by the flag.  flag will hold the poll type either
    'longPoll' or 'shortPoll'.

    Use this if you want your node server to do something at fixed
    intervals.
    """
    def poll(self, flag):
        if 'longPoll' in flag:
            LOGGER.debug('longPoll (controller)')
        else:
            LOGGER.debug('shortPoll (controller)')
            if self.motion == True:
                self.m_clear()

    def updateInfo(self, payload, topic: str):
        topic_suffix = topic.split('/')[-1]
        if topic_suffix == "availability":
            value = int(payload == "online")
            self.setDriver("ST", value)
        elif topic_suffix == "light":
            value = int(payload == "on")
            self.setDriver("GV0", value)
        elif topic_suffix == "door":
            if payload == "open":
                value = 1
            elif payload == "opening":
                value = 2
            elif payload == "stopped":
                value = 3
            elif payload == "closing":
                value = 4
            else:
                value = 0
            self.setDriver("GV1", value)
        elif topic_suffix == "motion":
            value = int(payload == "detected")
            self.motion = (payload == 'detected')
            self.setDriver("GV2", value)
        elif topic_suffix == "lock":
            value = int(payload == "locked")
            self.setDriver("GV3", value)
        elif topic_suffix == "obstruction":
            value = int(payload == "obstructed")
            self.setDriver("GV4", value)
        else:
            LOGGER.warn(f"Unable to handle data for topic {topic}")

    def lt_on(self, command):
        self.controller.mqtt_pub(self.cmd_topic + "light", "on")

    def lt_off(self, command):
        self.controller.mqtt_pub(self.cmd_topic + "light", "off")

    def dr_open(self, command):
        self.controller.mqtt_pub(self.cmd_topic + "door", "open")

    def dr_close(self, command):
        self.controller.mqtt_pub(self.cmd_topic + "door", "close")

    def dr_stop(self, command):
        self.controller.mqtt_pub(self.cmd_topic + "door", "stop")

    def lk_lock(self, command):
        self.controller.mqtt_pub(self.cmd_topic + "lock", "lock")

    def lk_unlock(self, command):
        self.controller.mqtt_pub(self.cmd_topic + "lock", "unlock")

    def m_clear(self, command=None):
        self.controller.mqtt_pub(self.device["status_topic"] + "/status/motion", "Clear")
        self.setDriver("GV2", 0)
        self.motion = False

    def query(self, command=None):
        """
        Called by ISY to report all drivers for this node. This is done in
        the parent class, so you don't need to override this method unless
        there is a need.
        """
        self.reportDrivers()
        
    # UOMs of interest:
    # 2: boolean
    # 25: index
    #
    # Driver controls of interest:
    # ST: Status
    # GV0: Custom Control 0
    # GV1: Custom Control 1
    # GV2: Custom Control 2
    # GV3: Custom Control 3
    # GV4: Custom Control 4
    # all the drivers - for reference
    drivers = [
        {"driver": "ST", "value": 0, "uom": 2},
        {"driver": "GV0", "value": 0, "uom": 2},
        {"driver": "GV1", "value": 0, "uom": 25},
        {"driver": "GV2", "value": 0, "uom": 2},
        {"driver": "GV3", "value": 0, "uom": 2},
        {"driver": "GV4", "value": 0, "uom": 2},
    ]

    """
    This is a dictionary of commands. If ISY sends a command to the NodeServer,
    this tells it which method to call. DON calls setOn, etc.
    """
    commands = {
        "QUERY": query,
        "DON": lt_on,
        "DOF": lt_off,
        "OPEN": dr_open,
        "CLOSE": dr_close,
        "STOP": dr_stop,
        "LOCK": lk_lock,
        "UNLOCK": lk_unlock,
        "MCLEAR": m_clear
        }
    
