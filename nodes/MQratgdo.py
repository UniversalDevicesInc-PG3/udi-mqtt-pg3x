"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2025

node MQratgdo

Class for Ratgdo Garage door opener for MYQ replacement
Able to control door, light, lock and get status of same as well as motion, obstruction
"""

# std libraries
pass

# external libraries
from udi_interface import Node, LOGGER

# personal libraries
pass

# Constants
DOOR_STATE_OPEN = 1
DOOR_STATE_OPENING = 2
DOOR_STATE_STOPPED = 3
DOOR_STATE_CLOSING = 4
DOOR_STATE_CLOSED = 0

DOOR_PAYLOAD_MAP = {
    "open": DOOR_STATE_OPEN,
    "opening": DOOR_STATE_OPENING,
    "stopped": DOOR_STATE_STOPPED,
    "closing": DOOR_STATE_CLOSING,
    "closed": DOOR_STATE_CLOSED,
}


class MQratgdo(Node):
    """Node representing a Ratgdo Garage Door Opener."""
    id = 'mqratgdo'

    def __init__(self, polyglot, primary, address, name, device):
        """Initializes the MQratgdo node.

        Args:
            polyglot: Reference to the Polyglot interface.
            primary: The address of the parent node.
            address: The address of this node.
            name: The name of this node.
            device: Dictionary containing device-specific information.
        """
        super().__init__(polyglot, primary, address, name)
        self.controller = self.poly.getNode(self.primary)
        self.lpfx = f'{address}:{name}'
        self.cmd_topic = device["cmd_topic"] + "/command/"
        self.device = device


    def updateInfo(self, payload: str, topic: str):
        """Updates node drivers based on MQTT messages from the Ratgdo device."""
        LOGGER.info(f"{self.lpfx} topic:{topic}, payload:{payload}")
        topic_suffix = topic.split('/')[-1]

        handler = {
            "availability": self._handle_availability,
            "light": self._handle_light,
            "door": self._handle_door,
            "motion": self._handle_motion,
            "lock": self._handle_lock,
            "obstruction": self._handle_obstruction,
        }.get(topic_suffix)

        if handler:
            handler(payload)
        else:
            LOGGER.warning(f"{self.lpfx} Unable to handle data for topic suffix: {topic_suffix}")
        LOGGER.debug(f"{self.lpfx} Exit updateInfo")


    def _handle_availability(self, payload: str):
        """Handles availability status updates."""
        value = 1 if payload == "online" else 0
        self.setDriver("ST", value)


    def _handle_light(self, payload: str):
        """Handles light status updates."""
        value = 1 if payload == "on" else 0
        self.setDriver("GV0", value)


    def _handle_door(self, payload: str):
        """Handles door status updates."""
        value = DOOR_PAYLOAD_MAP.get(payload, DOOR_STATE_CLOSED)
        self.setDriver("GV1", value)


    def _handle_motion(self, payload: str):
        """Handles motion detection status updates."""
        value = 1 if payload == "detected" else 0
        # self.motion = (payload == 'detected') # self.motion removed
        self.setDriver("GV2", value)


    def _handle_lock(self, payload: str):
        """Handles lock status updates."""
        value = 1 if payload == "locked" else 0
        self.setDriver("GV3", value)


    def _handle_obstruction(self, payload: str):
        """Handles obstruction status updates."""
        value = 1 if payload == "obstructed" else 0
        self.setDriver("GV4", value)


    def lt_on(self, command):
        """Handles the 'DON' command to turn the light on."""
        LOGGER.info(f"{self.lpfx} {command}")
        self.controller.mqtt_pub(self.cmd_topic + "light", "on")
        LOGGER.debug(f"{self.lpfx} Exit lt_on")


    def lt_off(self, command):
        """Handles the 'DOF' command to turn the light off."""
        LOGGER.info(f"{self.lpfx} {command}")
        self.controller.mqtt_pub(self.cmd_topic + "light", "off")
        LOGGER.debug(f"{self.lpfx} Exit lt_off")


    def dr_open(self, command):
        """Handles the 'OPEN' command to open the garage door."""
        LOGGER.info(f"{self.lpfx} {command}")
        self.controller.mqtt_pub(self.cmd_topic + "door", "open")
        LOGGER.debug(f"{self.lpfx} Exit dr_open")


    def dr_close(self, command):
        """Handles the 'CLOSE' command to close the garage door."""
        LOGGER.info(f"{self.lpfx} {command}")
        self.controller.mqtt_pub(self.cmd_topic + "door", "close")
        LOGGER.debug(f"{self.lpfx} Exit dr_close")


    def dr_stop(self, command):
        """Handles the 'STOP' command to stop the garage door."""
        LOGGER.info(f"{self.lpfx} {command}")
        self.controller.mqtt_pub(self.cmd_topic + "door", "stop")
        LOGGER.debug(f"{self.lpfx} Exit dr_stop")


    def lk_lock(self, command):
        """Handles the 'LOCK' command to lock the garage door."""
        LOGGER.info(f"{self.lpfx} {command}")
        self.controller.mqtt_pub(self.cmd_topic + "lock", "lock")
        LOGGER.debug(f"{self.lpfx} Exit lk_lock")


    def lk_unlock(self, command):
        """Handles the 'UNLOCK' command to unlock the garage door."""
        LOGGER.info(f"{self.lpfx} {command}")
        self.controller.mqtt_pub(self.cmd_topic + "lock", "unlock")
        LOGGER.debug(f"{self.lpfx} Exit lk_unlock")


    def m_clear(self, command=None):
        """Handles the 'MCLEAR' command to clear motion status."""
        LOGGER.info(f"{self.lpfx} {command}")
        self.controller.mqtt_pub(self.cmd_topic.replace("/command/", "/status/") + "motion", "Clear")
        self.setDriver("GV2", 0)
        LOGGER.debug(f"{self.lpfx} Exit m_clear")


    def query(self, command=None):
        """Handles the 'QUERY' command from ISY.

        This is called by ISY to report all drivers for this node.
        """
        LOGGER.info(f"{self.lpfx} {command}")
        self.reportDrivers()
        LOGGER.debug(f"{self.lpfx} Exit query")
        

    # all the drivers - for reference
    # UOMs of interest:
    # 2: boolean
    # 25: index
    #
    # Driver controls of interest:
    # ST: Status
    # GV0: Custom Control 0, light
    # GV1: Custom Control 1, door
    # GV2: Custom Control 2, motion
    # GV3: Custom Control 3, lock
    # GV4: Custom Control 4, obstruction
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