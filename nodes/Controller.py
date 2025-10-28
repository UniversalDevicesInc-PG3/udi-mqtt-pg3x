"""MQTT Polyglot NodeServer for EISY/Polisy.

This module provides the Controller class for the mqtt-poly-pg3x NodeServer,
which enables communication between MQTT devices and the EISY/Polisy home
automation system through the Polyglot interface.

The Controller manages MQTT connections, device discovery, and acts as the
central coordinator for all MQTT device nodes in the system.

Author: Stephen Jenkins
Copyright: (C) 2025 Stephen Jenkins
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
    'cmd_prefix': None
}

STATUS_TOPIC_PREFIX = 'stat/'
TELE_TOPIC_PREFIX = 'tele/'
RESULT_TOPIC_SUFFIX = '/RESULT'
STATUS10_TOPIC_SUFFIX = '/STATUS10'

# Sensor processor mapping for MQTT message processing
SENSOR_PROCESSORS = {
    'ANALOG': '_OA',
    'DS18B20': '_ODS', 
    'AM2301': '_OAM',
    'BME280': '_OBM'
}

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
    """Controller class for MQTT Polyglot NodeServer.
    
    The Controller serves as the main coordinator for the MQTT NodeServer,
    managing device discovery, MQTT connections, and communication between
    MQTT devices and the EISY/Polisy system.
    
    Attributes:
        id (str): Unique identifier for the controller node ('mqctrl').
        hb (int): Heartbeat counter for monitoring controller status.
        numNodes (int): Number of discovered device nodes.
        n_queue (list): Queue for tracking node creation completion.
        queue_condition (Condition): Threading condition for node queue synchronization.
        ready_event (Event): Event signaling when controller is ready for operation.
        all_handlers_st_event (Event): Event signaling when all handlers are complete.
        stop_sse_client_event (Event): Event for stopping SSE client operations.
        discovery_in (bool): Flag indicating if discovery is currently in progress.
        devlist (list): List of configured MQTT devices.
        status_topics (list): List of MQTT status topics to subscribe to.
        status_topics_to_devices (Dict[str, str]): Mapping of status topics to device addresses.
        valid_configuration (bool): Flag indicating if configuration is valid.
        mqttc (Client): MQTT client instance for communication.
        mqtt_server (str): MQTT broker server address.
        mqtt_port (int): MQTT broker port number.
        mqtt_user (str): MQTT broker username.
        mqtt_password (str): MQTT broker password.
        status_prefix (str): Prefix for MQTT status topics.
        cmd_prefix (str): Prefix for MQTT command topics.
        
    Example:
        The Controller is typically instantiated by the Polyglot interface
        and manages the entire MQTT device ecosystem.
    """
    id = 'mqctrl'

    def __init__(self, poly, primary, address, name):
        """Initialize the Controller node.
        
        Sets up the controller with all necessary attributes, data storage classes,
        event subscriptions, and initializes the node in the Polyglot system.
        
        Args:
            poly: Polyglot interface instance for communication with EISY/Polisy.
            primary: Primary node address (typically the controller itself).
            address: Unique address for this controller node.
            name: Human-readable name for the controller node.
            
        Note:
            This method initializes all internal data structures, sets up event
            handlers, creates data storage classes, and signals readiness to
            the Polyglot interface.
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
        """Initialize and start the MQTT NodeServer.
        
        This method is called by the Polyglot handler during startup. It performs
        the complete initialization sequence including profile updates, parameter
        loading, device discovery, and MQTT connection establishment.
        
        The startup process includes:
        1. Clearing notices and setting initial status
        2. Updating the ISY profile if necessary
        3. Setting custom parameters documentation
        4. Waiting for all handlers to complete initialization
        5. Performing device discovery
        6. Establishing MQTT connection
        7. Signaling readiness to child nodes
        
        Returns:
            None
            
        Note:
            If any step fails, the controller will set error status and display
            appropriate error messages in the notices.
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
        """Initialize and connect to the MQTT broker.
        
        Creates an MQTT client, configures connection parameters, and establishes
        a connection to the user's MQTT server. Configuration is loaded from
        Parameters, devfile, and defaults in that order of precedence.
        
        Returns:
            bool: True if connection successful, False otherwise.
            
        Note:
            This method will retry connection attempts and log appropriate
            error messages if the connection fails.
        """
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
        """Handle node creation completion notification.
        
        This method is called when a node has been successfully created by the
        Polyglot interface. It adds the node address to the internal queue
        and notifies waiting threads that the node creation is complete.
        
        The node_queue() and wait_for_node_done() methods work together to
        provide a simple synchronization mechanism for node creation. Since
        the addNode() API call is asynchronous and returns before the node
        is fully created, this allows the controller to wait until the node
        is ready before attempting to use it.
        
        Args:
            data (dict): Event data containing the node address.
            
        Returns:
            None
        """
        address = data.get('address')
        if address:
            with self.queue_condition:
                self.n_queue.append(address)
                self.queue_condition.notify()

    def wait_for_node_done(self):
        """Wait for a node creation to complete.
        
        This method blocks until a node has been successfully created and
        added to the internal queue. It works in conjunction with node_queue()
        to provide synchronization for asynchronous node creation.
        
        Returns:
            None
            
        Note:
            This method will timeout after 0.2 seconds if no node creation
            completion is received, allowing for non-blocking operation.
        """
        with self.queue_condition:
            while not self.n_queue:
                self.queue_condition.wait(timeout = 0.2)
            self.n_queue.pop()
        

    def dataHandler(self, data):
        """Handle custom data loading from Polyglot.
        
        This method is called when custom data is received from the Polyglot
        interface. It loads the data into the internal Data storage and
        signals completion of the data handler.
        
        Args:
            data: Custom data from Polyglot interface, can be None.
            
        Returns:
            None
        """
        LOGGER.debug(f'enter: Loading data {data}')
        if data is None:
            LOGGER.warning("No custom data")
        else:
            self.Data.load(data)
        self.handler_data_st = True
        self.check_handlers()


    def parameterHandler(self, params):
        """Handle custom parameters from Polyglot dashboard.
        
        This method is called via the CUSTOMPARAMS event when the user enters
        or updates custom parameters through the Polyglot dashboard. It loads
        the parameters into the internal Parameters storage and signals
        completion of the parameter handler.
        
        Args:
            params: Custom parameters from Polyglot interface.
            
        Returns:
            None
        """
        LOGGER.info('parmHandler: Loading parameters now')
        self.Parameters.load(params)
        self.handler_params_st = True
        LOGGER.info('parmHandler Done...')

        
    def typedParameterHandler(self, params):
        """Handle custom typed parameters from Polyglot.
        
        This method is called via the CUSTOMTYPEDPARAMS event when custom
        typed parameters are created. It loads the typed parameters into
        the internal TypedParameters storage and signals completion.
        
        Args:
            params: Custom typed parameters from Polyglot interface.
            
        Returns:
            None
        """
        LOGGER.debug('Loading typed parameters now')
        self.TypedParameters.load(params)
        LOGGER.debug(params)
        self.handler_typedparams_st = True
        self.check_handlers()


    def typedDataHandler(self, data):
        """Handle custom typed data from Polyglot dashboard.
        
        This method is called via the CUSTOMTYPEDDATA event when the user
        enters or updates custom typed parameters through the Polyglot dashboard.
        It loads the typed data into the internal TypedData storage and signals
        completion of the typed data handler.
        
        Args:
            data: Custom typed data from Polyglot interface, can be None.
            
        Returns:
            None
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
        """Check if all startup handlers have completed.
        
        This method verifies that all required startup handlers (parameters,
        data, typed parameters, and typed data) have completed their
        initialization. Once all handlers are complete, it sets the
        all_handlers_st_event to signal that startup can proceed.
        
        Returns:
            None
        """
        if (self.handler_params_st and self.handler_data_st and
            self.handler_typedparams_st and self.handler_typeddata_st):
            self.all_handlers_st_event.set()


    def checkParams(self):
        """Load and validate configuration parameters.
        
        Loads device configuration from either a YAML devfile or JSON devlist
        parameter. The devlist configuration takes precedence over devfile
        values and will update or overwrite existing configuration.
        
        Returns:
            bool: True if configuration loaded successfully, False otherwise.
            
        Note:
            At least one of devfile or devlist must be configured for
            successful operation.
        """
        
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
        """Load device configuration from YAML file.
        
        Loads device configuration from a YAML file specified in the devfile
        parameter. The YAML file should contain 'general' and 'devices' sections.
        The general section is converted from an array of dictionaries to a
        flat dictionary for easier access.
        
        Returns:
            bool: True if configuration loaded successfully, False otherwise.
            
        Raises:
            OSError: If the file cannot be opened.
            yaml.YAMLError: If the YAML file cannot be parsed.
        """
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
        """Load device configuration from JSON string.
        
        Loads device configuration from a JSON string specified in the devlist
        parameter. This configuration will update or add to the existing devlist
        that was initially loaded from the devfile.
        
        Returns:
            bool: True if configuration loaded successfully, False otherwise.
            
        Raises:
            json.JSONDecodeError: If the JSON string cannot be parsed.
            TypeError: If the data type is invalid.
        """
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
        """Update or insert device configuration by ID.
        
        Updates an existing device configuration in the list if a device with
        the same ID exists, or appends the new entry if no matching ID is found.
        
        Args:
            config_list (list): List of device configurations to update.
            new_entry (dict): New device configuration to add or update.
            
        Returns:
            None
        """
        new_id = new_entry.get('id')
        for i, entry in enumerate(config_list):
            if entry.get('id') == new_id:
                config_list[i] = new_entry  # Replace
                return
        config_list.append(new_entry)  # Append if not found


    def _load_mqtt_parameters(self) -> bool:
        """Load MQTT connection parameters with fallback hierarchy.
        
        Loads MQTT connection parameters using a fallback hierarchy:
        1. Parameters from Polyglot interface
        2. General configuration from devfile
        3. Default configuration values
        
        Returns:
            bool: True if parameters loaded successfully, False otherwise.
            
        Raises:
            ValueError: If parameter values cannot be converted to expected types.
            TypeError: If parameter types are invalid.
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
            self.cmd_prefix = self._get_str(
                self.Parameters.get("cmd_prefix"),
                self.general.get("cmd_prefix")
            )
        except (ValueError, TypeError) as ex:
            LOGGER.error(f"Failed to parse MQTT parameters: {ex}")
            return False
        return True

    
    def _get_str(*args: Optional[Any]) -> Optional[str]:
        """Get the first string value from a list of arguments.
        
        Searches through the provided arguments and returns the first one
        that is a string type, or None if no string is found.
        
        Args:
            *args: Variable number of arguments to search through.
            
        Returns:
            Optional[str]: First string found, or None if no string exists.
        """
        for val in args:
            if isinstance(val, str):
                return val
        return None

    def _get_int(*args: Optional[Any]) -> Optional[int]:
        """Get the first integer value from a list of arguments.
        
        Searches through the provided arguments and returns the first one
        that is an integer type or can be converted to an integer, or None
        if no valid integer is found.
        
        Args:
            *args: Variable number of arguments to search through.
            
        Returns:
            Optional[int]: First integer found, or None if no valid integer exists.
        """
        for val in args:
            if isinstance(val, int):
                return val
            if isinstance(val, str) and val.isdigit():
                return int(val)
        return None

    
    def handleLevelChange(self, level):
        """Handle log level changes from Polyglot.
        
        This method is called via the LOGLEVEL event when the log level
        is changed through the Polyglot interface. It updates the logging
        configuration based on the new level.
        
        Args:
            level (dict): Dictionary containing the new log level information.
            
        Returns:
            None
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
        """Handle polling events from Polyglot.
        
        This method is called by Polyglot for both short and long polling
        intervals. In the Controller, it only handles heartbeat functionality
        to maintain communication with the ISY.
        
        Args:
            flag (dict): Polling flag indicating the type of poll (short/long).
            
        Returns:
            None
        """
        # no updates until node is through start-up
        if not self.ready_event:
            LOGGER.error(f"Node not ready yet, exiting")
            return

        if 'shortPoll' in flag:
            LOGGER.debug('longPoll (controller)')
            self.heartbeat()


    def query(self, command=None):
        """Query all nodes in the system.
        
        This method queries all nodes managed by the controller, causing
        them to report their current driver values to the ISY. This is
        typically called during startup or when a manual query is requested.
        
        Args:
            command (str, optional): Command string for logging purposes.
            
        Returns:
            None
        """
        LOGGER.info(f"Enter {command}")
        nodes = self.poly.getNodes()
        for node in nodes:
            nodes[node].reportDrivers()
        LOGGER.debug(f"Exit")


    def discover_cmd(self, command=None):
        """Perform device discovery and node creation.
        
        This method is called both during controller startup and when a
        DISCOVER command is received from the ISY. It loads configuration
        parameters and performs device discovery to create or update nodes.
        
        Args:
            command (str, optional): Command string for logging purposes.
            
        Returns:
            bool: True if discovery completed successfully, False otherwise.
            
        Note:
            This method can be used after updating devfile or configuration
            to refresh the device list.
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
        """Discover devices and manage node lifecycle.
        
        Performs the actual device discovery process, including:
        1. Creating new nodes for discovered devices
        2. Cleaning up nodes that are no longer in the configuration
        3. Updating the node count
        
        Returns:
            bool: True if discovery completed successfully, False otherwise.
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
        """Discover and create device nodes.
        
        Validates device configurations, sets names and addresses, and creates
        new nodes for devices that don't already exist in the system.
        
        Args:
            nodes_existing (dict): Dictionary of existing nodes.
            nodes_new (list): List to track newly created nodes.
            
        Returns:
            None
        """
        LOGGER.info(f"discovery start")
        self.discovery_in = True
        for dev in self.devlist:
            if not self._validate_device_definition(dev):
                continue
                
            name = dev.get("name", dev["id"])  # Use friendly name or fallback to ID
            address = self._format_device_address(dev)
            
            if address not in nodes_existing:
                if not self._create_device_node(dev, name, address):
                    continue
                self.wait_for_node_done()
            nodes_new.append(address)
        LOGGER.info("Done adding nodes.")
        LOGGER.debug(f'DEVLIST: {self.devlist}')
        

    def _validate_device_definition(self, dev):
        """Validate device configuration has required fields.
        
        Checks that a device configuration contains all required fields
        for proper operation.
        
        Args:
            dev (dict): Device configuration to validate.
            
        Returns:
            bool: True if device is valid, False otherwise.
        """
        required_fields = ["id", "status_topic", "cmd_topic", "type"]
        if not all(field in dev for field in required_fields):
            LOGGER.error(f"Invalid device definition: {json.dumps(dev)}")
            return False
        return True
    

    def _create_device_node(self, dev, name, address):
        """Create a device node from configuration.
        
        Creates a new device node using the validated device configuration.
        The node type is determined from the device configuration and the
        appropriate node class is instantiated.
        
        Args:
            dev (dict): Device configuration.
            name (str): Human-readable name for the device.
            address (str): Unique address for the device node.
            
        Returns:
            bool: True if node created successfully, False otherwise.
        """
        device_type = dev["type"]
        
        # Check if device type is supported
        if device_type not in DEVICE_CONFIG:
            LOGGER.error(f"Device type {device_type} is not yet supported")
            return False
            
        # Get the node class
        device_config = DEVICE_CONFIG[device_type]
        node_class = device_config["node_class"]
        
        # Normalize the device's primary status topic
        dev["status_topic"] = self._normalize_topic(dev["status_topic"], self.status_prefix)

        # Normalize the device's control topic
        dev["cmd_topic"] = self._normalize_topic(dev["cmd_topic"], self.cmd_prefix)
        
        # Add status topics using device configuration
        self._add_device_status_topics(dev)

        # and create the node
        LOGGER.info(f"Adding {device_type}, {name}")
        self.poly.addNode(node_class(self.poly, self.address, address, name, dev))
        
        return True

    
    def _add_device_status_topics(self, dev):
        """Add status topics for a device based on its configuration.
        
        Adds MQTT status topics for a device based on its type and configuration.
        This includes both primary status topics and any extra topics defined
        in the device configuration.
        
        Args:
            dev (dict): Device configuration.
            
        Returns:
            None
        """
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
        """Add status topics and map them to device address.
        
        Adds a list of status topics to the subscription list and maps each
        topic to the corresponding device address for message routing.
        
        Args:
            dev (dict): Device configuration.
            status_topics (List[str]): List of MQTT status topics to add.
            
        Returns:
            None
        """
        device_address = self._format_device_address(dev)
        
        for raw_topic in status_topics:
            status_topic = self._normalize_topic(raw_topic, self.status_prefix)
            self.status_topics.append(status_topic)
            self.status_topics_to_devices[status_topic] = device_address
            

    def _normalize_topic(self, topic: Optional[str], prefix: Optional[str]) -> str:
        """Normalize MQTT topic by replacing placeholder with prefix.
        
        Replaces leading '~' in a topic with the given prefix. This allows
        for flexible topic configuration where '~' acts as a placeholder
        for the actual prefix.
        
        Args:
            topic (Optional[str]): MQTT topic to normalize.
            prefix (Optional[str]): Prefix to replace '~' with.
            
        Returns:
            str: Normalized topic string.
        """
        if topic is None:
            return ""
        if topic.startswith("~") and prefix is not None:
            return prefix + topic[1:]
        return topic
    
            
    def _cleanup_nodes(self, nodes_new, nodes_old):
        """Remove nodes that are no longer in the device list.
        
        Compares existing nodes with the current device list and removes
        any nodes that are no longer configured.
        
        Args:
            nodes_new (list): List of newly created nodes.
            nodes_old (list): List of existing nodes to check for removal.
            
        Returns:
            bool: Always returns True.
        """
        for node in nodes_old:
            if (node not in nodes_new):
                LOGGER.info(f"need to delete node {node}")
                self._remove_status_topics(node)
                self.poly.delNode(node)
                self.discovery_in = False
                LOGGER.info(f"Done Cleanup")
        return True

    
    def _remove_status_topics(self, node):
        """Remove status topics for a deleted node.
        
        Removes all status topics associated with a node that is being
        deleted from the system.
        
        Args:
            node (str): Node address to remove topics for.
            
        Returns:
            None
        """
        for status_topic in self.status_topics_to_devices:
            if self.status_topics_to_devices[status_topic] == self.poly.getNode(node):
                self.status_topics.remove(status_topic)
                self.status_topics_to_devices.pop(status_topic)
                LOGGER.info(f"remove topic = {status_topic}")
            # should be keyed to `id` instead of `status_topic`

            
    def _on_connect(self, _mqttc, _userdata, _flags, rc):
        """Handle MQTT connection events.
        
        This method is called when the MQTT client connects or fails to connect
        to the broker. It handles the connection result and initiates subscription
        to status topics on successful connection.
        
        Args:
            _mqttc: MQTT client instance (unused).
            _userdata: User data passed to the client (unused).
            _flags: Connection flags (unused).
            rc (int): Return code indicating connection result (0 = success).
            
        Returns:
            None
        """
        if rc == 0:
            LOGGER.info(f"Poly MQTT Connected")
            self.mqtt_subscribe()
        else:
            LOGGER.error(f"Poly MQTT Connect failed with rc:{rc}")

            
    def _on_disconnect(self, _mqttc, _userdata, rc):
        """Handle MQTT disconnection events.
        
        This method is called when the MQTT client disconnects from the broker.
        It handles both graceful disconnections and unexpected disconnections,
        attempting to reconnect if the disconnection was unexpected.
        
        Args:
            _mqttc: MQTT client instance (unused).
            _userdata: User data passed to the client (unused).
            rc (int): Return code indicating disconnection reason (0 = graceful).
            
        Returns:
            None
        """
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
        """Handle incoming MQTT messages.
        
        This method is called when an MQTT message is received. It processes
        the message payload and routes it to the appropriate device node based
        on the topic. Supports both JSON and plain text message formats.
        
        Args:
            _mqttc: MQTT client instance (unused).
            _userdata: User data passed to the client (unused).
            message: MQTT message object containing topic and payload.
            
        Returns:
            None
            
        Note:
            This method exits early if discovery is still in progress to avoid
            processing messages during device configuration.
        """
        if self.discovery_in:
            return
            
        topic = message.topic
        payload = message.payload.decode("utf-8")
        LOGGER.info(f"Received message from {topic}: {payload}")
        
        try:
            # Try to parse as JSON first
            data = self._parse_json_payload(payload)
            if data is not None:
                self._process_json_message(topic, payload, data)
            else:
                self._process_plain_text_message(topic, payload)
        except Exception as ex:
            LOGGER.error(f"Failed to process message from {topic}: {ex}")

            
    def _parse_json_payload(self, payload: str) -> Optional[Dict[str, Any]]:
        """Parse JSON payload with proper error handling.
        
        Args:
            payload (str): Raw message payload to parse.
            
        Returns:
            Optional[Dict[str, Any]]: Parsed JSON data or None if not JSON.
        """
        try:
            return json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            return None

        
    def _process_json_message(self, topic: str, payload: str, data: Dict[str, Any]) -> None:
        """Process JSON-formatted MQTT message.
        
        Args:
            topic (str): MQTT topic of the message.
            payload (str): Raw message payload.
            data (Dict[str, Any]): Parsed JSON data.
        """
        # Extract StatusSNS data if present
        if 'StatusSNS' in data:
            data = data['StatusSNS']
            LOGGER.debug(f'StatusSNS data: {data}')
        
        # Try to process as sensor data first
        if self._process_sensor_data(topic, payload, data):
            return
        
        # Process as regular JSON message
        LOGGER.debug(f'Processing JSON message: {payload}')
        self._route_message_to_device(topic, payload)

        
    def _process_sensor_data(self, topic: str, payload: str, data: Dict[str, Any]) -> bool:
        """Process sensor-specific data from JSON message.
        
        Args:
            topic (str): MQTT topic of the message.
            payload (str): Raw message payload.
            data (Dict[str, Any]): Parsed JSON data.
            
        Returns:
            bool: True if sensor data was processed, False otherwise.
        """
        for sensor_type, log_prefix in SENSOR_PROCESSORS.items():
            if sensor_type in data:
                sensors = self._extract_sensors(data, sensor_type)
                for sensor in sensors:
                    LOGGER.debug(f'{log_prefix}: {sensor}')
                    self._route_message_to_device(topic, payload, sensor)
                return True
        return False
    
    
    def _extract_sensors(self, data: Dict[str, Any], sensor_type: str) -> List[str]:
        """Extract sensor names from data based on sensor type.
        
        Args:
            data (Dict[str, Any]): JSON data containing sensor information.
            sensor_type (str): Type of sensor to extract.
            
        Returns:
            List[str]: List of sensor names.
        """
        if sensor_type == 'ANALOG':
            return data[sensor_type] if isinstance(data[sensor_type], list) else [data[sensor_type]]
        else:
            return [key for key in data.keys() if sensor_type in key]

        
    def _process_plain_text_message(self, topic: str, payload: str) -> None:
        """Process plain text MQTT message.
        
        Args:
            topic (str): MQTT topic of the message.
            payload (str): Raw message payload.
        """
        LOGGER.debug(f'Processing plain text message: {payload}')
        self._route_message_to_device(topic, payload)

        
    def _route_message_to_device(self, topic: str, payload: str, sensor: Optional[str] = None) -> None:
        """Route message to the appropriate device node.
        
        Args:
            topic (str): MQTT topic of the message.
            payload (str): Raw message payload.
            sensor (Optional[str]): Sensor name for sensor-specific routing.
        """
        try:
            if sensor:
                device_address = self._get_device_address_from_sensor_id(topic, sensor)
            else:
                device_address = self._dev_by_topic(topic)
            
            if device_address:
                self.poly.getNode(device_address).updateInfo(payload, topic)
            else:
                LOGGER.warning(f"No device found for topic: {topic}")
        except Exception as ex:
            LOGGER.error(f"Failed to route message to device: {ex}")

            
    def _dev_by_topic(self, topic: str) -> Optional[str]:
        """Get device address by MQTT topic.
        
        Performs a reverse lookup to find the device address associated with
        a given MQTT status topic. Since each status topic is unique, this
        provides a clean way to route messages to the correct device node.
        
        Args:
            topic (str): MQTT topic to look up.
            
        Returns:
            Optional[str]: Device address if found, None otherwise.
        """
        LOGGER.debug(f'STATUS TO DEVICES = {self.status_topics_to_devices.get(topic, None)}')
        return self.status_topics_to_devices.get(topic, None)

    
    def _get_device_address_from_sensor_id(self, topic: str, sensor_type: str) -> Optional[str]:
        """Get device address from sensor ID in JSON messages.
        
        This method is used for JSON messages from certain devices that contain
        sensor information. It looks up the device address using both the topic
        and sensor type information from the message data.
        
        Args:
            topic (str): MQTT topic of the received message.
            sensor_type (str): Type of sensor from the message data.
            
        Returns:
            Optional[str]: Device address if found, None otherwise.
            
        Note:
            Falls back to topic-based lookup if sensor ID lookup fails.
        """
        LOGGER.debug(f'GDA1: topic: {topic}  sensor_type: {sensor_type}')
        LOGGER.debug(f'GDA1b: devlist: {self.devlist}')
        
        topic_part = topic.rsplit('/')[1]
        
        # Look for device with matching sensor_id
        for device in self.devlist:
            LOGGER.debug(f'GDA2: device: {device}')
            if ('sensor_id' in device and 
                topic_part in device['status_topic'] and 
                sensor_type in device['sensor_id']):
                node_id = self._format_device_address(device)
                LOGGER.debug(f'GDA2b: NODE_ID: {node_id}, {topic}, {sensor_type}')
                return node_id
        
        # Fallback to topic-based lookup
        LOGGER.debug(f'GDA3: NODE_ID2: None')
        node_id = self._dev_by_topic(topic)
        LOGGER.debug(f'GDA4: revert to topic NODE_ID3: {node_id}')
        return node_id

    
    def _format_device_address(self, dev) -> str:
        """Format device address for ISY compatibility.
        
        Creates a device address from the device ID that is compatible with
        ISY address requirements. The address is limited to 14 characters
        and special characters are normalized.
        
        Args:
            dev (dict): Device configuration containing the 'id' field.
            
        Returns:
            str: Formatted device address suitable for ISY.
        """        
        # was return dev["id"].lower().replace("_", "").replace("-", "_")[:DEVICE_ADDRESS_MAX_LENGTH]
        # poly funciton:
        # def getValidAddress(self, name):
        #     name = bytes(name, 'utf-8').decode('utf-8','ignore')
        #     return re.sub(r"[<>`~!@#$%^&*(){}[\]?/\\;:\"'\-]+", "", name.lower())[:14]

        # retaining former replace function for backward compatibility
        name = dev["id"].replace("_", "").replace("-", "_")
        return self.poly.getValidAddress(name)

    
    def mqtt_pub(self, topic, message):
        """Publish a message to an MQTT topic.
        
        Publishes a message to the specified MQTT topic using the connected
        MQTT client. This is used to send commands to MQTT devices.
        
        Args:
            topic (str): MQTT topic to publish to.
            message (str): Message content to publish.
            
        Returns:
            None
        """

        LOGGER.debug(f"mqtt_pub: topic: {topic}, message: {message}")
        self.mqttc.publish(topic, message, retain=False)

        
    def mqtt_subscribe(self):
        """Subscribe to MQTT status topics.
        
        This method is called when the MQTT client connects or reconnects
        to subscribe to all configured status topics. It logs the success
        or failure of each subscription attempt.
        
        Returns:
            None
        """
        LOGGER.info("Poly MQTT subscribing...")
        result = 255
        results = []
        for stopic in self.status_topics:
            results.append((stopic, tuple(self.mqttc.subscribe(stopic))))
            
        for (topic, (result, mid)) in results:
            if result == 0:
                LOGGER.info(f"Subscribed to {topic} MID: {mid}, res: {result}")
            else:
                LOGGER.error(f"Failed to subscribe {topic} MID: {mid}, res: {result}")
                
        for node in self.poly.getNodes():
            if node != self.address:
                self.poly.getNode(node).query()
        LOGGER.info("Subscriptions Done")


    def delete(self, command=None):
        """Handle NodeServer deletion.
        
        This method is called by Polyglot when the NodeServer is being deleted.
        If the process is co-resident and controlled by Polyglot, it will be
        terminated within 5 seconds of receiving this message.
        
        Args:
            command (str, optional): Command string for logging purposes.
            
        Returns:
            None
        """
        LOGGER.info(command)
        self.setDriver('ST', 0, report = True, force = True)
        LOGGER.info('bye bye ... deleted.')


    def stop(self, command=None):
        """Handle NodeServer shutdown.
        
        This method is called by Polyglot when the NodeServer is being stopped.
        It provides an opportunity to cleanly disconnect from MQTT broker and
        perform other shutdown tasks.
        
        Args:
            command (str, optional): Command string for logging purposes.
            
        Returns:
            None
        """
        LOGGER.info(command)
        self.setDriver('ST', 0, report = True, force = True)
        self.Notices.clear()
        if self.mqttc:
            self.mqttc.loop_stop()
            self.mqttc.disconnect()
        LOGGER.info('NodeServer stopped.')


    def heartbeat(self):
        """Send heartbeat signal to ISY.
        
        This function uses the long poll interval to alternately send ON and OFF
        commands back to the ISY. Programs on the ISY can monitor this heartbeat
        to determine if the NodeServer is running properly.
        
        Returns:
            None
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


