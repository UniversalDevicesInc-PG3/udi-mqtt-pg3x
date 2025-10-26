""" mqtt-poly-pg3x NodeServer/Plugin for EISY/Polisy

(C) 2025 Stephen Jenkins

Controller class
"""

# std libraries
import json, yaml, time, logging
from threading import Event, Condition
from typing import Dict, List, Optional, Any

# external libraries
from udi_interface import Node, LOGGER, Custom, LOG_HANDLER
from paho.mqtt.client import Client
from paho.mqtt.enums import CallbackAPIVersion

# personal libraries
pass

# Nodes
from nodes import *

DEFAULT_CONFIG = {
    'mqtt_server': 'localhost',
    'mqtt_port': 1884,
    'mqtt_user': 'admin',
    'mqtt_password': 'admin',
    'status_prefix': None,
    'control_prefix': None
}

STATUS_TOPIC_PREFIX = 'stat/'
TELE_TOPIC_PREFIX = 'tele/'
RESULT_TOPIC_SUFFIX = '/RESULT'
STATUS10_TOPIC_SUFFIX = '/STATUS10'
DEVICE_ADDRESS_MAX_LENGTH = 14

# Comprehensive device configuration mapping
DEVICE_CONFIG = {
    'switch': {'node_class': MQSwitch,},
    'dimmer': {'node_class': MQDimmer,
        'extra_status_topics': lambda dev: [dev['status_topic'].rsplit('/', 1)[0] + RESULT_TOPIC_SUFFIX]},
    'ifan': {'node_class': MQFan,},
    'sensor': {'node_class': MQSensor,},
    'flag': {'node_class': MQFlag,},
    'TempHumid': {'node_class': MQdht, 'extra_status_topics': lambda dev: [dev['status_topic'].rsplit('/', 1)[0] +
                                        STATUS10_TOPIC_SUFFIX.replace(TELE_TOPIC_PREFIX, STATUS_TOPIC_PREFIX)]
    },
    'Temp': {'node_class': MQds, 'extra_status_topics': lambda dev: [dev['status_topic'].rsplit('/', 1)[0] +
                                       STATUS10_TOPIC_SUFFIX.replace(TELE_TOPIC_PREFIX, STATUS_TOPIC_PREFIX)]},
    'TempHumidPress': {'node_class': MQbme, 'extra_status_topics': lambda dev: [dev['status_topic'].rsplit('/', 1)[0] +
                                       STATUS10_TOPIC_SUFFIX.replace(TELE_TOPIC_PREFIX, STATUS_TOPIC_PREFIX)]},
    'distance': {
        'node_class': MQhcsr,
    },
    'shellyflood': {
        'node_class': MQShellyFlood,
        'status_topics': lambda dev: dev["status_topic"]  # Already a list
    },
    'analog': {
        'node_class': MQAnalog,
        'extra_status_topics': lambda dev: [dev['status_topic'].rsplit('/', 1)[0] +
                                       STATUS10_TOPIC_SUFFIX.replace(TELE_TOPIC_PREFIX, STATUS_TOPIC_PREFIX)]},
    's31': {'node_class': MQs31,},
    'raw': {'node_class': MQraw,},
    'RGBW': {'node_class': MQRGBWstrip,},
    'ratgdo': {'node_class': MQratgdo, 'status_topics': lambda dev: [dev["status_topic"] + "/status/availability",
                                                                dev["status_topic"] + "/status/light",
                                                                dev["status_topic"] + "/status/door",
                                                                dev["status_topic"] + "/status/motion",
                                                                dev["status_topic"] + "/status/lock",
                                                                dev["status_topic"] + "/status/obstruction"]}
}


class Controller(Node):
    id = 'mqctrl'

    def __init__(self, poly, primary, address, name):
        """
        super
        self definitions
        data storage classes
        subscribes
        ready
        we exist!
        """
        super().__init__(poly, primary, address, name)

        # importand flags, timers, vars
        self.hb = 0 # heartbeat
        self.numNodes = 0

        # storage arrays & conditions
        self.n_queue = []
        self.queue_condition = Condition()

        # Events & in
        self.ready_event = Event()
        self.all_handlers_st_event = Event()
        self.stop_sse_client_event = Event()
        self.discovery_in = False

        # startup completion flags
        self.handler_params_st = None
        self.handler_data_st = None
        self.handler_typedparams_st = None
        self.handler_typeddata_st = None

        self.devlist = []       
        # e.g. [{'id': 'topic1', 'type': 'switch', 'status_topic': 'stat/topic1/power',
        # 'cmd_topic': 'cmnd/topic1/power'}]
        self.status_topics = []
        
        # Maps to device IDs
        self.status_topics_to_devices: Dict[str, str] = {}
        self.valid_configuration = False

        # Create data storage classes
        self.Notices         = Custom(poly, 'notices')
        self.Parameters      = Custom(poly, 'customparams')
        self.Data            = Custom(poly, 'customdata')
        self.TypedParameters = Custom(poly, 'customtypedparams')
        self.TypedData       = Custom(poly, 'customtypeddata')

        # Subscribe to various events from the Interface class.
        self.poly.subscribe(self.poly.START,             self.start, address)
        self.poly.subscribe(self.poly.POLL,              self.poll)
        self.poly.subscribe(self.poly.LOGLEVEL,          self.handleLevelChange)
        self.poly.subscribe(self.poly.CUSTOMPARAMS,      self.parameterHandler)
        self.poly.subscribe(self.poly.CUSTOMDATA,        self.dataHandler)
        self.poly.subscribe(self.poly.STOP,              self.stop)
        self.poly.subscribe(self.poly.DISCOVER,          self.discover_cmd)
        self.poly.subscribe(self.poly.CUSTOMTYPEDDATA,   self.typedDataHandler)
        self.poly.subscribe(self.poly.CUSTOMTYPEDPARAMS, self.typedParameterHandler)
        self.poly.subscribe(self.poly.ADDNODEDONE,       self.node_queue)

        # Tell the interface we have subscribed to all the events we need.
        # Once we call ready(), the interface will start publishing data.
        self.poly.ready()

        # Tell the interface we exist.  
        self.poly.addNode(self, conn_status='ST')
        

    def start(self):
        """
        Called by handler during startup.
        """
        LOGGER.info(f"Virtual Devices PG3 NodeServer {self.poly.serverdata['version']}")
        self.Notices.clear()
        self.Notices['hello'] = 'Start-up'
        self.setDriver('ST', 1, report = True, force = True)

        # Send the profile files to the ISY if neccessary or version changed.
        self.poly.updateProfile()

        # Send the default custom parameters documentation file to Polyglot
        self.poly.setCustomParamsDoc()

        # Initializing a heartbeat
        self.heartbeat()

        # Wait for all handlers to finish
        LOGGER.warning(f'Waiting for all handlers to complete...')
        self.Notices['waiting'] = 'Waiting on valid configuration'
        self.all_handlers_st_event.wait(timeout=60)
        if not self.all_handlers_st_event.is_set():
            # start-up failed
            LOGGER.error("Timed out waiting for handlers to startup")
            self.setDriver('ST', 2) # start-up failed
            self.Notices['error'] = 'Error start-up timeout.  Check config & restart'
            return

        # Discover and wait for discovery to complete
        discoverSuccess = self.discover_cmd()

        # first update from Gateway
        if not discoverSuccess:
            # start-up failed
            LOGGER.error(f'First discovery failed!!! exit {self.name}')
            self.Notices['error'] = 'Error first discovery.  Check config & restart'
            self.setDriver('ST', 2)
            return

        # Discover and wait for discovery to complete
        mqttSuccess = self._mqtt_start()

        # first update from Gateway
        if not mqttSuccess:
            # start-up failed
            LOGGER.error(f'MQTT connection failed!!! exit {self.name}')
            self.Notices['error'] = 'Error MQTT connection.  Check config & restart'
            self.setDriver('ST', 2)
            return

        self.Notices.delete('waiting')        
        LOGGER.info('Started MQTT NodeServer v%s', self.poly.serverdata)
        self.query(command = f"{self.name}: STARTUP")

        # signal to the nodes, its ok to start
        self.ready_event.set()

        # clear inital start-up message
        if self.Notices.get('hello'):
            self.Notices.delete('hello')

        LOGGER.info(f'exit {self.name}')

        
    def _mqtt_start(self):
        """Initialize and connect to the user's MQTT server."""
        self.mqttc = Client(CallbackAPIVersion.VERSION1)
        self.mqttc.on_connect = self._on_connect
        self.mqttc.on_disconnect = self._on_disconnect  # type: ignore
        self.mqttc.on_message = self._on_message
        self.mqttc.username_pw_set(self.mqtt_user, self.mqtt_password)

        try:
            assert self.mqtt_server is not None, "mqtt_server must be set"
            assert self.mqtt_port is not None, "mqtt_port must be set"
            self.mqttc.connect(self.mqtt_server, self.mqtt_port, keepalive=10)
            self.mqttc.loop_start()
        except Exception as ex:
            LOGGER.error(f"Error connecting to Poly MQTT broker: {ex}")
            self.Notices['mqtt'] = 'Error on user MQTT connection'
            return False  # Early exit on failure

        while not self.mqttc.is_connected():
            LOGGER.error("Start: Waiting on user MQTT connection")
            self.Notices['mqtt'] = 'Waiting on user MQTT connection'
            time.sleep(3)

        self.Notices.clear()
        self.mqtt_subscribe()
        LOGGER.info("Start Done...")
        return True


    def node_queue(self, data):
        '''
        node_queue() and wait_for_node_event() create a simple way to wait
        for a node to be created.  The nodeAdd() API call is asynchronous and
        will return before the node is fully created. Using this, we can wait
        until it is fully created before we try to use it.
        '''
        address = data.get('address')
        if address:
            with self.queue_condition:
                self.n_queue.append(address)
                self.queue_condition.notify()

    def wait_for_node_done(self):
        with self.queue_condition:
            while not self.n_queue:
                self.queue_condition.wait(timeout = 0.2)
            self.n_queue.pop()
        

    def dataHandler(self,data):
        LOGGER.debug(f'enter: Loading data {data}')
        if data is None:
            LOGGER.warning("No custom data")
        else:
            self.Data.load(data)
        self.handler_data_st = True
        self.check_handlers()


    def parameterHandler(self, params):
        """
        Called via the CUSTOMPARAMS event. When the user enters or
        updates Custom Parameters via the dashboard.
        """
        LOGGER.info('parmHandler: Loading parameters now')
        self.Parameters.load(params)
        self.handler_params_st = True
        LOGGER.info('parmHandler Done...')

        
    def typedParameterHandler(self, params):
        """
        Called via the CUSTOMTYPEDPARAMS event. This event is sent When
        the Custom Typed Parameters are created.
        """
        LOGGER.debug('Loading typed parameters now')
        self.TypedParameters.load(params)
        LOGGER.debug(params)
        self.handler_typedparams_st = True
        self.check_handlers()


    def typedDataHandler(self, data):
        """
        Called via the CUSTOMTYPEDDATA event. This event is sent when
        the user enters or updates Custom Typed Parameters via the dashboard.
        'params' will be the full list of parameters entered by the user.
        """
        LOGGER.debug('Loading typed data now')
        if data is None:
            LOGGER.warning("No custom data")
        else:
            self.TypedData.load(data)
        LOGGER.debug(f'Loaded typed data {data}')
        self.handler_typeddata_st = True
        self.check_handlers()


    def check_handlers(self):
        """
        Once all start-up parameters are done then set event.
        """
        if (self.handler_params_st and self.handler_data_st and
            self.handler_typedparams_st and self.handler_typeddata_st):
            self.all_handlers_st_event.set()


    def checkParams(self):
        """Load and validate configuration parameters from devfile or devlist."""
        
        # Load device configuration from YAML file
        if self.Parameters.get("devfile"):
            if not self._load_devfile_config():
                return False
        
        # Load device configuration from JSON string
        elif self.Parameters.get("devlist"):
            if not self._load_devlist_config():
                return False
        else:
            LOGGER.error("checkParams: No devfile or devlist configured! Must be configured.")
            return False

        # Load MQTT parameters with fallback to general config
        if not self._load_mqtt_parameters():
            return False
        # Success
        return True
    

    def _load_devfile_config(self):
        """Load device configuration from YAML file."""
        devfile_path = self.Parameters["devfile"]
        if not devfile_path or not isinstance(devfile_path, str):
            LOGGER.error("Invalid devfile path provided")
            return False
            
        try:
            with open(devfile_path, 'r', encoding='utf-8') as file:
                dev_yaml = yaml.safe_load(file)
        except (OSError, yaml.YAMLError) as ex:
            error_type = "open" if isinstance(ex, OSError) else "parse"
            LOGGER.error(f"Failed to {error_type} {devfile_path}: {ex}")
            return False
        
        if "devices" not in dev_yaml:
            LOGGER.error(f"Manual discovery file {devfile_path} is missing devices section")
            return False
        devices = dev_yaml.get("devices")
        general = dev_yaml.get("general", [])
        LOGGER.info(f"devices = {devices}")
        LOGGER.info(f"general = {general}")
        
        # initial device list is based on devfile items
        self.devlist = devices

        # these are the general configuration items based on devfile
        self.general = {k: v for d in general for k, v in d.items()}
        return True
    

    def _load_devlist_config(self):
        """Load device configuration from JSON string."""
        devlist_data = self.Parameters["devlist"]
        if not devlist_data:
            LOGGER.error("No devlist data provided")
            return False
            
        try:
            if isinstance(devlist_data, str):
                parsed_data = json.loads(devlist_data)
            else:
                parsed_data = devlist_data
                
            if not isinstance(parsed_data, dict):
                LOGGER.error("Devlist data must be a dictionary")
                return False

            # devlist items take precidence over devfile
            self.upsert_by_id(self.devlist, parsed_data)
        except (json.JSONDecodeError, TypeError) as ex:
            LOGGER.error(f"Failed to parse devlist: {ex}")
            return False
        return True
    

    def upsert_by_id(self, config_list, new_entry):
        """
        Update list of devices if same id  or append if does not exist.
        """
        new_id = new_entry.get('id')
        for i, entry in enumerate(config_list):
            if entry.get('id') == new_id:
                config_list[i] = new_entry  # Replace
                return
        config_list.append(new_entry)  # Append if not found


    def _load_mqtt_parameters(self) -> bool:
        """
        Load MQTT connection parameters with fallback taken in order
        of Parameter list, then devfile, and finally defaults.
        """
        try:
            self.mqtt_server = self._get_str(
                self.Parameters.get("mqtt_server"),
                self.general.get("mqtt_server"),
                DEFAULT_CONFIG.get("mqtt_server")
            )
            self.mqtt_port = self._get_int(
                self.Parameters.get("mqtt_port"),
                self.general.get("mqtt_port"),
                DEFAULT_CONFIG.get("mqtt_port")
            )
            
            self.mqtt_user = self._get_str(
                self.Parameters.get("mqtt_user"),
                self.general.get("mqtt_user"),
                DEFAULT_CONFIG.get("mqtt_user")
            )
            self.mqtt_password = self._get_str(
                self.Parameters.get("mqtt_password"),
                self.general.get("mqtt_password"),
                DEFAULT_CONFIG.get("mqtt_password")
            )
            self.status_prefix = self._get_str(
                self.Parameters.get("status_prefix"),
                self.general.get("status_prefix")
            )
            self.control_prefix = self._get_str(
                self.Parameters.get("control_prefix"),
                self.general.get("control_prefix")
            )
        except (ValueError, TypeError) as ex:
            LOGGER.error(f"Failed to parse MQTT parameters: {ex}")
            return False
        return True

    
    def _get_str(*args: Optional[Any]) -> Optional[str]:
        for val in args:
            if isinstance(val, str):
                return val
        return None

    def _get_int(*args: Optional[Any]) -> Optional[int]:
        for val in args:
            if isinstance(val, int):
                return val
            if isinstance(val, str) and val.isdigit():
                return int(val)
        return None

    
    def handleLevelChange(self, level):
        """
        Called via the LOGLEVEL event, to handle log level change.
        """
        LOGGER.info(f'enter: level={level}')
        if level['level'] < 10:
            LOGGER.info("Setting basic config to DEBUG...")
            LOG_HANDLER.set_basic_config(True,logging.DEBUG)
        else:
            LOGGER.info("Setting basic config to WARNING...")
            LOG_HANDLER.set_basic_config(True,logging.WARNING)
        LOGGER.info(f'exit: level={level}')


    def poll(self, flag):
        """
        Short & Long polling, only heartbeat in Controller
        """
        # no updates until node is through start-up
        if not self.ready_event:
            LOGGER.error(f"Node not ready yet, exiting")
            return

        if 'shortPoll' in flag:
            LOGGER.debug('longPoll (controller)')
            self.heartbeat()


    def query(self, command = None):
        """
        Query all nodes from the gateway.
        """
        LOGGER.info(f"Enter {command}")
        nodes = self.poly.getNodes()
        for node in nodes:
            nodes[node].reportDrivers()
        LOGGER.debug(f"Exit")


    def discover_cmd(self, command = None):
        """
        Call node discovery here. Called from controller start method
        and from DISCOVER command received from ISY.
        Calls checkParams, so can be used after update of devFile or config
        """
        LOGGER.info(command)
        success = False
        if self.discovery_in:
            LOGGER.info('Discover already running.')
            return success

        self.discovery_in = True
        LOGGER.info("In Discovery...")

        if self.checkParams() and self._discover():
            success = True
            LOGGER.info("Discovery Success")
        else:
            LOGGER.error("Discovery Failure")
        self.discovery_in = False            
        return success


    def _discover(self):
        """
        Discover all nodes from the gateway.
        """
        success = False
        nodes_existing = self.poly.getNodes()
        LOGGER.debug(f"current nodes = {nodes_existing}")
        nodes_old = [node for node in nodes_existing if node != self.id]
        nodes_new = []

        try:
            self._discover_nodes(nodes_existing, nodes_new)
            self._cleanup_nodes(nodes_new, nodes_old)
            self.numNodes = len(nodes_new)
            self.setDriver('GV0', self.numNodes)
            success = True
            LOGGER.info(f"Discovery complete. success = {success}")
        except Exception as ex:
            LOGGER.error(f'Discovery Failure: {ex}', exc_info=True)            
        return success


    def _discover_nodes(self, nodes_existing, nodes_new):
        LOGGER.info(f"discovery start")
        self.discovery_in = True
        for dev in self.devlist:
            if not self._validate_device_definition(dev):
                continue
                
            name = dev.get("name", dev["id"])  # Use friendly name or fallback to ID
            address = Controller._format_device_address(dev)
            
            if address not in nodes_existing:
                if not self._create_device_node(dev, name, address):
                    continue
                self.wait_for_node_done()
            nodes_new.append(address)
        LOGGER.info("Done adding nodes.")
        LOGGER.debug(f'DEVLIST: {self.devlist}')

    def _validate_device_definition(self, dev):
        """Validate that device has required fields."""
        required_fields = ["id", "status_topic", "cmd_topic", "type"]
        if not all(field in dev for field in required_fields):
            LOGGER.error(f"Invalid device definition: {json.dumps(dev)}")
            return False
        return True

    def _create_device_node(self, dev, name, address):
        """Create a device node using the device configuration."""
        device_type = dev["type"]
        
        # Check if device type is supported
        if device_type not in DEVICE_CONFIG:
            LOGGER.error(f"Device type {device_type} is not yet supported")
            return False
            
        # Get the node class and create the node
        device_config = DEVICE_CONFIG[device_type]
        node_class = device_config["node_class"]
        LOGGER.info(f"Adding {device_type}, {name}")
        self.poly.addNode(node_class(self.poly, self.address, address, name, dev))
        
        # Add status topics using device configuration
        self._add_device_status_topics(dev)
        return True

    def _add_device_status_topics(self, dev):
        """Add status topics for a device based on its configuration."""
        device_type = dev["type"]
        device_config = DEVICE_CONFIG.get(device_type, {})
        
        # Get primary status topics
        if "status_topics" in device_config:
            # Custom status topics (like shellyflood, ratgdo)
            status_topics = device_config["status_topics"](dev)
            self._add_status_topics(dev, status_topics)
        else:
            # Default single status topic
            self._add_status_topics(dev, [dev["status_topic"]])
        
        # Add extra status topics if configured
        if "extra_status_topics" in device_config:
            extra_topics = device_config["extra_status_topics"](dev)
            # Store extra status topic in device for logging
            if extra_topics:
                dev['extra_status_topic'] = extra_topics[0]
                LOGGER.info(f'Adding EXTRA {dev["extra_status_topic"]} for {dev.get("name", dev["id"])}')
            self._add_status_topics(dev, extra_topics)

        
    def _add_status_topics(self, dev, status_topics: List[str]):
        """Add status topics for a device and map them to the device address."""
        device_address = Controller._format_device_address(dev)
        
        for status_topic in status_topics:
            self.status_topics.append(status_topic)
            self.status_topics_to_devices[status_topic] = device_address

            
    def _cleanup_nodes(self, nodes_new, nodes_old):    
        # routine to remove nodes which exist but are not in devlist
        for node in nodes_old:
            if (node not in nodes_new):
                LOGGER.info(f"need to delete node {node}")
                self._remove_status_topics(node)
                self.poly.delNode(node)
                self.discovery_in = False
                LOGGER.info(f"Done Cleanup")
        return True

    
    def _remove_status_topics(self, node):
        for status_topic in self.status_topics_to_devices:
            if self.status_topics_to_devices[status_topic] == self.poly.getNode(node):
                self.status_topics.remove(status_topic)
                self.status_topics_to_devices.pop(status_topic)
                LOGGER.info(f"remove topic = {status_topic}")
            # should be keyed to `id` instead of `status_topic`

            
    def _on_connect(self, _mqttc, _userdata, _flags, rc):
        if rc == 0:
            LOGGER.info(f"Poly MQTT Connected")
            self.mqtt_subscribe()
        else:
            LOGGER.error(f"Poly MQTT Connect failed with rc:{rc}")

            
    def _on_disconnect(self, _mqttc, _userdata, rc):
        if rc != 0:
            LOGGER.warning("Poly MQTT disconnected, trying to re-connect")
            try:
                self.mqttc.reconnect()
            except Exception as ex:
                LOGGER.error(f"Error connecting to Poly MQTT broker {ex}")
                return False
        else:
            LOGGER.info("Poly MQTT graceful disconnection")

            
    def _on_message(self, _mqttc, _userdata, message):
        if self.discovery_in:
            return
        topic = message.topic
        payload = message.payload.decode("utf-8")
        LOGGER.info(f"Received _on_message {payload} from {topic}")
        try:
            try:
                data = json.loads(payload)
                if 'StatusSNS' in data:
                    data = data['StatusSNS']
                    LOGGER.info(f'_StatusSNS data: {data}')
                # Process different sensor types
                sensor_processors = {
                    'ANALOG': '_OA',
                    'DS18B20': '_ODS', 
                    'AM2301': '_OAM',
                    'BME280': '_OBM'
                }
                
                processed = False
                for sensor_type, log_prefix in sensor_processors.items():
                    if sensor_type in data:
                        if sensor_type == 'ANALOG':
                            sensors = data[sensor_type]
                        else:
                            sensors = [key for key in data.keys() if sensor_type in key]
                        
                        for sensor in sensors:
                            LOGGER.info(f'{log_prefix}: {sensor}')
                            self.poly.getNode(self._get_device_address_from_sensor_id(topic, sensor)).updateInfo(
                                payload, topic)
                        processed = True
                        break
                
                if not processed:  # if it's anything else, process as usual
                    LOGGER.info(f'_else: Payload = {payload}, Topic = {topic}')
                    self.poly.getNode(self._dev_by_topic(topic)).updateInfo(payload, topic)
            except (json.decoder.JSONDecodeError, TypeError):  # if it's not a JSON, process as usual
                LOGGER.info(f"_NotJSON: Payload = {payload}, Topic = {topic}")
                self.poly.getNode(self._dev_by_topic(topic)).updateInfo(payload, topic)
        except Exception as ex:
            LOGGER.error(f"Failed to process message {ex}")

            
    def _dev_by_topic(self, topic: str) -> Optional[str]:
        LOGGER.debug(f'STATUS TO DEVICES = {self.status_topics_to_devices.get(topic, None)}')
        return self.status_topics_to_devices.get(topic, None)

    
    def _get_device_address_from_sensor_id(self, topic: str, sensor_type: str) -> Optional[str]:
        LOGGER.debug(f'GDA1: topic: {topic}  sensor_type: {sensor_type}')
        LOGGER.debug(f'GDA1b: devlist: {self.devlist}')
        
        topic_part = topic.rsplit('/')[1]
        
        # Look for device with matching sensor_id
        for device in self.devlist:
            LOGGER.debug(f'GDA2: device: {device}')
            if ('sensor_id' in device and 
                topic_part in device['status_topic'] and 
                sensor_type in device['sensor_id']):
                node_id = Controller._format_device_address(device)
                LOGGER.debug(f'GDA2b: NODE_ID: {node_id}, {topic}, {sensor_type}')
                return node_id
        
        # Fallback to topic-based lookup
        LOGGER.debug(f'GDA3: NODE_ID2: None')
        node_id = self._dev_by_topic(topic)
        LOGGER.debug(f'GDA4: revert to topic NODE_ID3: {node_id}')
        return node_id

    
    @staticmethod
    def _format_device_address(dev) -> str:
        return dev["id"].lower().replace("_", "").replace("-", "_")[:DEVICE_ADDRESS_MAX_LENGTH]

    
    def mqtt_pub(self, topic, message):
        LOGGER.debug(f"mqtt_pub: topic: {topic}, message: {message}")
        self.mqttc.publish(topic, message, retain=False)

        
    def mqtt_subscribe(self):
        LOGGER.info("Poly MQTT subscribing...")
        result = 255
        results = []
        for stopic in self.status_topics:
            results.append((stopic, tuple(self.mqttc.subscribe(stopic))))
        for (topic, (result, mid)) in results:
            if result == 0:
                LOGGER.info(
                    f"Subscribed to {topic} MID: {mid}, res: {result}"
                )
            else:
                LOGGER.error(
                    f"Failed to subscribe {topic} MID: {mid}, res: {result}"
                )
        for node in self.poly.getNodes():
            if node != self.address:
                self.poly.getNode(node).query()
        LOGGER.info("Subscriptions Done")


    def delete(self, command = None):
        """
        This is called by Polyglot upon deletion of the NodeServer. If the
        process is co-resident and controlled by Polyglot, it will be
        terminiated within 5 seconds of receiving this message.
        """
        LOGGER.info(command)
        self.setDriver('ST', 0, report = True, force = True)
        LOGGER.info('bye bye ... deleted.')


    def stop(self, command = None):
        """
        This is called by Polyglot when the node server is stopped.  You have
        the opportunity here to cleanly disconnect from your device or do
        other shutdown type tasks.
        """
        LOGGER.info(command)
        self.setDriver('ST', 0, report = True, force = True)
        self.Notices.clear()
        if self.mqttc:
            self.mqttc.loop_stop()
            self.mqttc.disconnect()
        LOGGER.info('NodeServer stopped.')


    def heartbeat(self):
        """
        Heartbeat function uses the long poll interval to alternately send a ON and OFF
        command back to the ISY.  Programs on the ISY can then monitor this.
        """
        LOGGER.debug(f'heartbeat: hb={self.hb}')
        command = "DOF" if self.hb else "DON"
        self.reportCmd(command, 2)
        self.hb = not self.hb
        LOGGER.debug("Exit")


    # Status that this node has. Should match the 'sts' section
    # of the nodedef file.
    drivers = [
        {'driver': 'ST', 'value': 1, 'uom': 25, 'name': "Controller Status"},
        {'driver': 'GV0', 'value': 0, 'uom': 107, 'name': "NumberOfNodes"},
    ]

    # Commands that this node can handle.  Should match the
    # 'accepts' section of the nodedef file.
    commands = {
        'DISCOVER': discover_cmd,
        'QUERY': query,
    }


