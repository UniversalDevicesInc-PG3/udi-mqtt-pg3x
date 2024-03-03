"""
mqtt-poly NodeServer/Plugin for EISY/Polisy

(C) 2024

node MQSensor
"""

import udi_interface

LOGGER = udi_interface.LOGGER

class MQSensor(udi_interface.Node):
    id = "mqsens"
    
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
        self.on = False
        self.motion = False

    def updateInfo(self, payload, topic: str):
        try:
            data = json.loads(payload)
        except Exception as ex:
            LOGGER.error("Failed to parse MQTT Payload as Json: {} {}".format(ex, payload))
            return False

        # motion detector
        if "motion" in data:
            if data["motion"] == "standby":
                self.setDriver("ST", 0)
                if self.motion:
                    self.motion = False
                    self.reportCmd("DOF")
            else:
                self.setDriver("ST", 1)
                if not self.motion:
                    self.motion = True
                    self.reportCmd("DON")
        else:
            self.setDriver("ST", 0)
        # temperature
        if "temperature" in data:
            self.setDriver("CLITEMP", data["temperature"])
        # heatIndex
        if "heatIndex" in data:
            self.setDriver("GPV", data["heatIndex"])
        # humidity
        if "humidity" in data:
            self.setDriver("CLIHUM", data["humidity"])
        # light detector reading
        if "ldr" in data:
            self.setDriver("LUMIN", data["ldr"])
        # LED
        if "state" in data:
            # LED is present
            if data["state"] == "ON":
                self.setDriver("GV0", 100)
            else:
                self.setDriver("GV0", 0)
            if "brightness" in data:
                self.setDriver("GV1", data["brightness"])
            if "color" in data:
                if "r" in data["color"]:
                    self.setDriver("GV2", data["color"]["r"])
                if "g" in data["color"]:
                    self.setDriver("GV3", data["color"]["g"])
                if "b" in data["color"]:
                    self.setDriver("GV4", data["color"]["b"])

    def led_on(self, command):
        self.controller.mqtt_pub(self.cmd_topic, json.dumps({"state": "ON"}))

    def led_off(self, command):
        self.controller.mqtt_pub(self.cmd_topic, json.dumps({"state": "OFF"}))

    def led_set(self, command):
        query = command.get("query")
        red = self._check_limit(int(query.get("R.uom100")))
        green = self._check_limit(int(query.get("G.uom100")))
        blue = self._check_limit(int(query.get("B.uom100")))
        brightness = self._check_limit(int(query.get("I.uom100")))
        transition = int(query.get("D.uom58"))
        flash = int(query.get("F.uom58"))
        cmd = {
            "state": "ON",
            "brightness": brightness,
            "color": {"r": red, "g": green, "b": blue},
        }
        if transition > 0:
            cmd["transition"] = transition
        if flash > 0:
            cmd["flash"] = flash
        self.controller.mqtt_pub(self.cmd_topic, json.dumps(cmd))

    def _check_limit(self, value):
        if value > 255:
            return 255
        elif value < 0:
            return 0
        else:
            return value
            
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
        {"driver": "CLITEMP", "value": 0, "uom": 17},
        {"driver": "GPV", "value": 0, "uom": 17},
        {"driver": "CLIHUM", "value": 0, "uom": 22},
        {"driver": "LUMIN", "value": 0, "uom": 36},
        {"driver": "GV0", "value": 0, "uom": 78},
        {"driver": "GV1", "value": 0, "uom": 100},
        {"driver": "GV2", "value": 0, "uom": 100},
        {"driver": "GV3", "value": 0, "uom": 100},
        {"driver": "GV4", "value": 0, "uom": 100},
        ]

    """
    This is a dictionary of commands. If ISY sends a command to the NodeServer,
    this tells it which method to call. DON calls setOn, etc.
    """
    commands = {
        "QUERY": query,
        "DON": led_on,
        "DOF": led_off,
        "SETLED": led_set
        }

