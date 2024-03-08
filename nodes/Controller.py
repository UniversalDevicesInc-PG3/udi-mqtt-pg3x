"""
mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2024

controller mqctrl
"""

import udi_interface

from typing import Dict, List
import paho.mqtt.client as mqtt
import json
import yaml
import time

# Nodes
from nodes import MQSwitch
from nodes import MQDimmer
from nodes import MQFan
from nodes import MQSensor
from nodes import MQFlag
from nodes import MQdht
from nodes import MQds
from nodes import MQbme
from nodes import MQhcsr
from nodes import MQShellyFlood
from nodes import MQAnalog
from nodes import MQs31
from nodes import MQraw
from nodes import MQRGBWstrip
from nodes import MQratgdo

"""
Some shortcuts for udi interface components

- LOGGER: to create log entries
- Custom: to access the custom data class
- ISY:    to communicate directly with the ISY (not commonly used)
"""
LOGGER = udi_interface.LOGGER
LOG_HANDLER = udi_interface.LOG_HANDLER
Custom = udi_interface.Custom
ISY = udi_interface.ISY

class Controller(udi_interface.Node):
    id = 'mqctrl'

    def __init__(self, polyglot, primary, address, name):
        """
        super
        self definitions
        data storage classes
        subscribes
        ready
        we exist!
        """
        super().__init__(polyglot, primary, address, name)

        # useful global variables
        self.poly = polyglot
        self.primary = primary # defined as self.address by main
        self.address = address
        self.name = name
        self.n_queue = []

        # here are specific variables to this controller
        self.discovery = False
        self.mqtt_server = "localhost"
        self.mqtt_port = 1884
        self.mqtt_user = 'admin'
        self.mqtt_password = 'admin'
        self.devlist = {}
        # e.g. [{'id': 'topic1', 'type': 'switch', 'status_topic': 'stat/topic1/power',
        # 'cmd_topic': 'cmnd/topic1/power'}]
        self.status_topics = []
        # Maps to device IDs
        self.status_topics_to_devices: Dict[str, str] = {}
        self.valid_configuration = False

        # Create data storage classes to hold specific data that we need
        # to interact with.  
        self.Parameters = Custom(polyglot, 'customparams')
        self.Notices = Custom(polyglot, 'notices')
        self.TypedParameters = Custom(polyglot, 'customtypedparams')
        self.TypedData = Custom(polyglot, 'customtypeddata')

        # Subscribe to various events from the Interface class.
        self.poly.subscribe(self.poly.START, self.start, address)
        self.poly.subscribe(self.poly.LOGLEVEL, self.handleLevelChange)
        self.poly.subscribe(self.poly.CUSTOMPARAMS, self.parameterHandler)
        self.poly.subscribe(self.poly.CUSTOMTYPEDPARAMS, self.typedParameterHandler)
        self.poly.subscribe(self.poly.CUSTOMTYPEDDATA, self.typedDataHandler)
        self.poly.subscribe(self.poly.POLL, self.poll)
        self.poly.subscribe(self.poly.STOP, self.stop)
        self.poly.subscribe(self.poly.DISCOVER, self.discover)
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)

        # Tell the interface we have subscribed to all the events we need.
        # Once we call ready(), the interface will start publishing data.
        self.poly.ready()

        # Tell the interface we exist.  
        self.poly.addNode(self)
        
        '''
        node_queue() and wait_for_node_event() create a simple way to wait
        for a node to be created.  The nodeAdd() API call is asynchronous and
        will return before the node is fully created. Using this, we can wait
        until it is fully created before we try to use it.
        '''
    def node_queue(self, data):
        self.n_queue.append(data['address'])

    def wait_for_node_done(self):
        while len(self.n_queue) == 0:
            time.sleep(0.1)
        self.n_queue.pop()

    def start(self):
        self.Notices['hello'] = 'Start-up'

        while self.valid_configuration is False:
            LOGGER.info('Waiting on valid configuration')
            self.Notices['waiting'] = 'Waiting on valid configuration'
            time.sleep(5)

        self.last = 0.0
        # Send the profile files to the ISY if neccessary. The profile version
        # number will be checked and compared. If it has changed since the last
        # start, the new files will be sent.
        self.poly.updateProfile()

        # Send the default custom parameters documentation file to Polyglot
        # for display in the dashboard.
        self.poly.setCustomParamsDoc()

        # Initializing a heartbeat is an example of something you'd want
        # to do during start.  Note that it is not required to have a
        # heartbeat in your node server
        self.heartbeat(True)

        # get user mqtt server connection going
        self.mqttc = mqtt.Client()
        self.mqttc.on_connect = self._on_connect
        self.mqttc.on_disconnect = self._on_disconnect
        self.mqttc.on_message = self._on_message
        self.mqttc.username_pw_set(self.mqtt_user, self.mqtt_password)
        try:
            self.mqttc.connect(self.mqtt_server, self.mqtt_port, 10)
            self.mqttc.loop_start()
        except Exception as ex:
            LOGGER.error("Error connecting to Poly MQTT broker {}".format(ex))
            self.Notices['mqtt'] = 'Error on user MQTT connection'
            # return False ; not compatible with start
        connected = self.mqttc.is_connected()
        while connected != True:
            LOGGER.error('Waiting on user MQTT connection')
            self.Notices['mqtt'] = 'Waiting on user MQTT connection'
            time.sleep(3)
            connected = self.mqttc.is_connected()
        self.removeNoticesAll()
        LOGGER.info("Start Done...")

    """
    Called via the CUSTOMPARAMS event. When the user enters or
    updates Custom Parameters via the dashboard. The full list of
    parameters will be sent to your node server via this event.

    Here we're loading them into our local storage so that we may
    use them as needed.

    New or changed parameters are marked so that you may trigger
    other actions when the user changes or adds a parameter.

    NOTE: Be carefull to not change parameters here. Changing
    parameters will result in a new event, causing an infinite loop.
    """
    def parameterHandler(self, params):
        self.removeNoticesAll()
        self.Parameters.load(params)
        LOGGER.debug('Loading parameters now')
        if self.checkParams():
            self.discover()


    """
    Called via the CUSTOMTYPEDPARAMS event. This event is sent When
    the Custom Typed Parameters are created.  See the checkParams()
    below.  Generally, this event can be ignored.

    Here we're re-load the parameters into our local storage.
    The local storage should be considered read-only while processing
    them here as changing them will cause the event to be sent again,
    creating an infinite loop.
    """
    def typedParameterHandler(self, params):
        self.TypedParameters.load(params)
        LOGGER.debug('Loading typed parameters now')
        LOGGER.debug(params)

    def checkParams(self):
        # pull in Parameters from Node Server Configuration page
        self.mqtt_server = self.Parameters["mqtt_server"] or 'localhost'
        self.mqtt_port = int(self.Parameters["mqtt_port"] or 1884)
        self.mqtt_ = int(self.Parameters["mqtt_port"] or 1884)
        self.mqtt_port = int(self.Parameters["mqtt_port"] or 1884)
        self.mqtt_user = self.Parameters["mqtt_user"] or 'admin'
        self.mqtt_password = self.Parameters["mqtt_password"] or 'admin'

        # upload the device topics yaml file (multiple devices)
        if self.Parameters["devfile"] is not None:
            try:
                x = self.Parameters["devfile"]
                f = open(x)
            except Exception as ex:
                LOGGER.error("Failed to open {}: {}".format(self.Parameters["devfile"], ex))
                return False
            try:
                dev_yaml = yaml.safe_load(f.read())  # upload devfile into data
                f.close()
            except Exception as ex:
                LOGGER.error(
                    "Failed to parse {} content: {}".format(self.Parameters["devfile"], ex))
                return False
            if "devices" not in dev_yaml:
                LOGGER.error(
                    "Manual discovery file {} is missing bulbs section".format(self.Parameters["devfile"]))
                return False
            self.devlist = dev_yaml["devices"]  # transfer devfile into devlist

        # upload the device topic from the Node Server Configuration Page
        elif self.Parameters["devlist"] is not None:
            try:
                x= self.Parameters['devlist']
                if type(x) == str:
                    self.devlist = json.loads(x)
            except Exception as ex:
                LOGGER.error("Failed to parse the devlist: {}".format(ex))
                return False
        else:
            LOGGER.error("devlist must be configured")
            return False

        self.valid_configuration = True

        return True

    """
    Called via the CUSTOMTYPEDDATA event. This event is sent when
    the user enters or updates Custom Typed Parameters via the dashboard.
    'params' will be the full list of parameters entered by the user.

    Here we're loading them into our local storage so that we may
    use them as needed.  The local storage should be considered 
    read-only while processing them here as changing them will
    cause the event to be sent again, creating an infinite loop.
    """
    def typedDataHandler(self, params):
        self.TypedData.load(params)
        LOGGER.debug('Loading typed data now')
        LOGGER.debug(params)

    """
    Called via the LOGLEVEL event.
    """
    def handleLevelChange(self, level):
        LOGGER.info('New log level: {}'.format(level))

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
            LOGGER.debug('longPoll re-parse updateallfromserver (controller)')
        else:
            LOGGER.debug('shortPoll check for events (controller)')

    def query(self, command = None):
        """
        The query method will be called when the ISY attempts to query the
        status of the node directly.  You can do one of two things here.
        You can send the values currently held by Polyglot back to the
        ISY by calling reportDriver() or you can actually query the 
        device represented by the node and report back the current 
        status.
        """
        LOGGER.info(f"Query")
        nodes = self.poly.getNodes()
        for node in nodes:
            nodes[node].reportDrivers()


    def updateProfile(self,command):
        LOGGER.info('update profile')
        st = self.poly.updateProfile()
        return st

    def discover(self, command = None):
        """
        Do discovery here. Called from controller start method
        and from DISCOVER command received from ISY
        parse out the devices contained in devlist.
        """
        LOGGER.info(f"discovery start")
        self.discovery = True
        nodes_new = []
        for dev in self.devlist:
            if (
                    "id" not in dev
                    or "status_topic" not in dev
                    or "cmd_topic" not in dev
                    or "type" not in dev
            ):
                LOGGER.error("Invalid device definition: {}".format(json.dumps(dev)))
                continue
            if "name" in dev:
                name = dev["name"]
            else:
                name = dev["id"]  # if there is no 'friendly name' use the ID instead
            address = Controller._format_device_address(dev)
            if not self.poly.getNode(address):
                if dev["type"] == "switch":
                    LOGGER.info("Adding {} {}".format(dev["type"], name))
                    self.poly.addNode(MQSwitch(self.poly, self.address, address, name, dev))
                    self._add_status_topics(dev, [dev["status_topic"]])

                elif dev["type"] == "dimmer":
                    LOGGER.info("Adding {} {}".format(dev["type"], name))
                    self.poly.addNode(MQDimmer(self.poly, self.address, address, name, dev))
                    self._add_status_topics(dev, [dev["status_topic"]])
                    dev['extra_status_topic'] = dev['status_topic'].rsplit('/', 1)[0] + '/RESULT'
                    LOGGER.info(f'Adding {dev["extra_status_topic"]}')
                    self._add_status_topics(dev, [dev['extra_status_topic']])
                    LOGGER.info("ADDED {} {} /RESULT".format(dev["type"], name))

                elif dev["type"] == "ifan":
                    LOGGER.info("Adding {} {}".format(dev["type"], name))
                    self.poly.addNode(MQFan(self.poly, self.address, address, name, dev))
                    self._add_status_topics(dev, [dev["status_topic"]])

                elif dev["type"] == "sensor":
                    LOGGER.info("Adding {} {}".format(dev["type"], name))
                    self.poly.addNode(MQSensor(self.poly, self.address, address, name, dev))
                    self._add_status_topics(dev, [dev["status_topic"]])

                elif dev["type"] == "flag":
                    LOGGER.info("Adding {} {}".format(dev["type"], name))
                    self.poly.addNode(MQFlag(self.poly, self.address, address, name, dev))
                    self._add_status_topics(dev, [dev["status_topic"]])

                elif dev["type"] == "TempHumid":
                    LOGGER.info("Adding {} {}".format(dev["type"], name))
                    self.poly.addNode(MQdht(self.poly, self.address, address, name, dev))
                    self._add_status_topics(dev, [dev["status_topic"]])
                    # parse status_topic to add 'STATUS10' MQTT message. Handles QUERY Response
                    extra_status_topic = dev['status_topic'].rsplit('/', 1)[0] + '/STATUS10'
                    dev['extra_status_topic'] = extra_status_topic.replace('tele/', 'stat/')
                    LOGGER.info(f'Adding EXTRA {dev["extra_status_topic"]} for {name}')
                    self._add_status_topics(dev, [dev['extra_status_topic']])

                elif dev["type"] == "Temp":
                    LOGGER.info("Adding {} {}".format(dev["type"], name))
                    self.poly.addNode(MQds(self.poly, self.address, address, name, dev))
                    self._add_status_topics(dev, [dev["status_topic"]])
                    # parse status_topic to add 'STATUS10' MQTT message. Handles QUERY Response
                    extra_status_topic = dev['status_topic'].rsplit('/', 1)[0] + '/STATUS10'
                    dev['extra_status_topic'] = extra_status_topic.replace('tele/', 'stat/')
                    LOGGER.info(f'Adding EXTRA {dev["extra_status_topic"]} for {name}')
                    self._add_status_topics(dev, [dev['extra_status_topic']])

                elif dev["type"] == "TempHumidPress":
                    LOGGER.info("Adding {} {}".format(dev["type"], name))
                    self.poly.addNode(MQbme(self.poly, self.address, address, name, dev))
                    self._add_status_topics(dev, [dev["status_topic"]])
                    # parse status_topic to add 'STATUS10' MQTT message. Handles QUERY Response
                    extra_status_topic = dev['status_topic'].rsplit('/', 1)[0] + '/STATUS10'
                    dev['extra_status_topic'] = extra_status_topic.replace('tele/', 'stat/')
                    LOGGER.info(f'Adding EXTRA {dev["extra_status_topic"]} for {name}')
                    self._add_status_topics(dev, [dev['extra_status_topic']])

                elif dev["type"] == "distance":
                    LOGGER.info("Adding {} {}".format(dev["type"], name))
                    self.poly.addNode(MQhcsr(self.poly, self.address, address, name, dev))
                    self._add_status_topics(dev, [dev["status_topic"]])

                elif dev["type"] == "shellyflood":
                    LOGGER.info(f"Adding {dev['type']} {name}")
                    self.poly.addNode(MQShellyFlood(self.poly, self.address, address, name, dev))
                    status_topics = dev["status_topic"]
                    self._add_status_topics(dev, status_topics)

                elif dev["type"] == "analog":
                    LOGGER.info("Adding {} {}".format(dev["type"], name))
                    self.poly.addNode(MQAnalog(self.poly, self.address, address, name, dev))
                    self._add_status_topics(dev, [dev["status_topic"]])
                    # parse status_topic to add 'STATUS10' MQTT message. Handles QUERY Response
                    extra_status_topic = dev['status_topic'].rsplit('/', 1)[0] + '/STATUS10'
                    dev['extra_status_topic'] = extra_status_topic.replace('tele/', 'stat/')
                    LOGGER.info(f'Adding EXTRA {dev["extra_status_topic"]} for {name}')
                    self._add_status_topics(dev, [dev['extra_status_topic']])

                elif dev["type"] == "s31":
                    LOGGER.info("Adding {} {}".format(dev["type"], name))
                    self.poly.addNode(MQs31(self.poly, self.address, address, name, dev))
                    self._add_status_topics(dev, [dev["status_topic"]])

                elif dev["type"] == "raw":
                    LOGGER.info("Adding {} {}".format(dev["type"], name))
                    self.poly.addNode(MQraw(self.poly, self.address, address, name, dev))
                    self._add_status_topics(dev, [dev["status_topic"]])

                elif dev["type"] == "RGBW":
                    LOGGER.info("Adding {} {}".format(dev["type"], name))
                    self.poly.addNode(MQRGBWstrip(self.poly, self.address, address, name, dev))
                    self._add_status_topics(dev, [dev["status_topic"]])

                elif dev["type"] == "ratgdo":
                    LOGGER.info("Adding {} {}".format(dev["type"], name))
                    self.poly.addNode(MQratgdo(self.poly, self.address, address, name, dev))
                    status_topics_base = dev["status_topic"] + "/status/"
                    status_topics = [status_topics_base + "availability",
                                     status_topics_base + "light",
                                     status_topics_base + "door",
                                     status_topics_base + "motion",
                                     status_topics_base + "lock",
                                     status_topics_base + "obstruction"]
                    self._add_status_topics(dev, status_topics)

                else:
                    LOGGER.error("Device type {} is not yet supported".format(dev["type"]))
                    continue
                self.wait_for_node_done()
            nodes_new.append(address)
        LOGGER.info("Done adding nodes.")
        LOGGER.debug(f'DEVLIST: {self.devlist}')

        # routine to remove nodes which exist but are not in devlist
        nodes = self.poly.getNodes()
        nodes_get = {key: nodes[key] for key in nodes if key != self.id}
        for node in nodes_get:
            if (node not in nodes_new):
                LOGGER.info(f"need to delete node {node}")
                self._remove_status_topics(node)
                self.poly.delNode(node)
        self.discovery = False
        LOGGER.info(f"Done Discovery")
        return True
                    
    def delete(self):
        """
        This is called by Polyglot upon deletion of the NodeServer. If the
        process is co-resident and controlled by Polyglot, it will be
        terminiated within 5 seconds of receiving this message.
        """
        LOGGER.info('bye bye ... deleted.')

    def stop(self):
        """
        This is called by Polyglot when the node server is stopped.  You have
        the opportunity here to cleanly disconnect from your device or do
        other shutdown type tasks.
        """
        LOGGER.info("MQTT is stopping")
        if self.mqttc is not None:
            self.mqttc.loop_stop()
            self.mqttc.disconnect()
        self.poly.stop()

        LOGGER.info('MQTT stopped.')

    def heartbeat(self,init=False):
        """
        This is a heartbeat function.  It uses the
        long poll interval to alternately send a ON and OFF command back to
        the ISY.  Programs on the ISY can then monitor this and take action
        when the heartbeat fails to update.
        """
        LOGGER.debug('heartbeat: init={}'.format(init))
        if init is not False:
            self.hb = init
        LOGGER.debug('heartbeat: hb={}'.format(self.hb))
        if self.hb == 0:
            self.reportCmd("DON",2)
            self.hb = 1
        else:
            self.reportCmd("DOF",2)
            self.hb = 0

    def removeNoticesAll(self, command = None):
        LOGGER.info('remove_notices_all: notices={}'.format(self.Notices))
        # Remove all existing notices
        self.Notices.clear()

    def _add_status_topics(self, dev, status_topics: List[str]):
        for status_topic in status_topics:
            self.status_topics.append(status_topic)
            self.status_topics_to_devices[status_topic] = Controller._format_device_address(dev)
            # should be keyed to `id` instead of `status_topic`

    def _remove_status_topics(self, node):
        for status_topic in self.status_topics_to_devices:
            if self.status_topics_to_devices[status_topic] == self.poly.getNode(node):
                self.status_topics.remove(status_topic)
                self.status_topics_to_devices.pop(status_topic)
                LOGGER.info(f"remove topic = {status_topic}")
            # should be keyed to `id` instead of `status_topic`

    def _on_connect(self, mqttc, userdata, flags, rc):
        if rc == 0:
            LOGGER.info("Poly MQTT Connected, subscribing...")
            results = []
            for stopic in self.status_topics:
                results.append((stopic, tuple(self.mqttc.subscribe(stopic))))
            for (topic, (result, mid)) in results:
                if result == 0:
                    LOGGER.info(
                        "Subscribed to {} MID: {}, res: {}".format(topic, mid, result)
                    )
                else:
                    LOGGER.error(
                        "Failed to subscribe {} MID: {}, res: {}".format(
                            topic, mid, result
                        )
                    )
            for node in self.poly.getNodes():
                if node != self.address:
                    self.poly.getNode(node).query()
        else:
            LOGGER.error("Poly MQTT Connect failed")

    def _on_disconnect(self, mqttc, userdata, rc):
        if rc != 0:
            LOGGER.warning("Poly MQTT disconnected, trying to re-connect")
            try:
                self.mqttc.reconnect()
            except Exception as ex:
                LOGGER.error("Error connecting to Poly MQTT broker {}".format(ex))
                return False
        else:
            LOGGER.info("Poly MQTT graceful disconnection")

    def _on_message(self, mqttc, userdata, message):
        if self.discovery == True:
            return
        topic = message.topic
        payload = message.payload.decode("utf-8")
        LOGGER.debug("Received _on_message {} from {}".format(payload, topic))
        try:
            try:
                data = json.loads(payload)
                if 'StatusSNS' in data:
                    data = data['StatusSNS']
                if 'ANALOG' in data.keys():
                    LOGGER.info('ANALOG Payload = {}, Topic = {}'.format(payload, topic))
                    for sensor in data['ANALOG']:
                        LOGGER.info(f'_OA: {sensor}')
                        self.poly.getNode(self._get_device_address_from_sensor_id(topic, sensor)).updateInfo(
                            payload, topic)
                for sensor in [sensor for sensor in data.keys() if 'DS18B20' in sensor]:
                    LOGGER.info(f'_ODS: {sensor}')
                    self.poly.getNode(self._get_device_address_from_sensor_id(topic, sensor)).updateInfo(payload, topic)
                for sensor in [sensor for sensor in data.keys() if 'AM2301' in sensor]:
                    LOGGER.info(f'_OAM: {sensor}')
                    self.poly.getNode(self._get_device_address_from_sensor_id(topic, sensor)).updateInfo(payload, topic)
                for sensor in [sensor for sensor in data.keys() if 'BME280' in sensor]:
                    LOGGER.info(f'_OBM: {sensor}')
                    self.poly.getNode(self._get_device_address_from_sensor_id(topic, sensor)).updateInfo(payload, topic)
                else:  # if it's anything else, process as usual
                    LOGGER.info('Payload = {}, Topic = {}'.format(payload, topic))
                    self.poly.getNode(self._dev_by_topic(topic)).updateInfo(payload, topic)
            except json.decoder.JSONDecodeError:  # if it's not a JSON, process as usual
                LOGGER.info('Payload = {}, Topic = {}'.format(payload, topic))
                self.poly.getNode(self._dev_by_topic(topic)).updateInfo(payload, topic)
        except Exception as ex:
            LOGGER.error("Failed to process message {}".format(ex))

    def _dev_by_topic(self, topic):
        LOGGER.debug(f'STATUS TO DEVICES = {self.status_topics_to_devices.get(topic, None)}')
        return self.status_topics_to_devices.get(topic, None)

    def _get_device_address_from_sensor_id(self, topic, sensor_type):
        LOGGER.debug(f'GDA1: {topic}  {sensor_type}')
        LOGGER.debug(f'DLT: {self.devlist}')
        self.node_id = None
        for device in self.devlist:
            LOGGER.debug(f'GDA2: {device}')
            if 'sensor_id' in device:
                if topic.rsplit('/')[1] in device['status_topic'] and sensor_type in device['sensor_id']:
                    self.node_id = device['id'].lower().replace("_", "").replace("-", "_")[:14]
                    LOGGER.debug(f'NODE_ID: {self.node_id}, {topic}, {sensor_type}')
                    break
        LOGGER.debug(f'NODE_ID2: {self.node_id}')
        return self.node_id

    @staticmethod
    def _format_device_address(dev) -> str:
        return dev["id"].lower().replace("_", "").replace("-", "_")[:14]

    def mqtt_pub(self, topic, message):
        self.mqttc.publish(topic, message, retain=False)


    # Status that this node has. Should match the 'sts' section
    # of the nodedef file.
    drivers = [
        {"driver": "ST", "value": 1, "uom": 2, "name": "NS Online"},
    ]

    # Commands that this node can handle.  Should match the
    # 'accepts' section of the nodedef file.
    commands = {
        'DISCOVER': discover,
        'QUERY': query,
    }


