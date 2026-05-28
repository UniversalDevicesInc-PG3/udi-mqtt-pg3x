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
import json
import logging
from threading import Event, Condition
from typing import Dict, List, Optional, Any

# external libraries
from udi_interface import Node, LOGGER, Custom, LOG_HANDLER

# local modules
from . import config_loader
from .constants import SENSOR_PROCESSORS
from .device_registry import DEVICE_CONFIG
from .mqtt_bridge import MqttBridge


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

    id = "mqctrl"

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
        self.hb = 0  # heartbeat
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
        self.general: Dict[str, Any] = {}
        self.status_topics = []

        # Maps to device IDs
        self.status_topics_to_devices: Dict[str, str] = {}
        self.valid_configuration = False
        self.mqtt_bridge: Optional[MqttBridge] = None

        # Create data storage classes
        self.Notices = Custom(poly, "notices")
        self.Parameters = Custom(poly, "customparams")
        self.Data = Custom(poly, "customdata")
        self.TypedParameters = Custom(poly, "customtypedparams")
        self.TypedData = Custom(poly, "customtypeddata")

        # Subscribe to various events from the Interface class.
        self.poly.subscribe(self.poly.START, self.start, address)
        self.poly.subscribe(self.poly.POLL, self.poll)
        self.poly.subscribe(self.poly.LOGLEVEL, self.handleLevelChange)
        self.poly.subscribe(self.poly.CUSTOMPARAMS, self.parameterHandler)
        self.poly.subscribe(self.poly.CUSTOMDATA, self.dataHandler)
        self.poly.subscribe(self.poly.STOP, self.stop)
        self.poly.subscribe(self.poly.DISCOVER, self.discover_cmd)
        self.poly.subscribe(self.poly.CUSTOMTYPEDDATA, self.typedDataHandler)
        self.poly.subscribe(self.poly.CUSTOMTYPEDPARAMS, self.typedParameterHandler)
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)

        # Tell the interface we have subscribed to all the events we need.
        # Once we call ready(), the interface will start publishing data.
        self.poly.ready()

        # Tell the interface we exist.
        self.poly.addNode(self, conn_status="ST")

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
        self.Notices["hello"] = "Start-up"
        self.setDriver("ST", 1, report=True, force=True)

        # Send the profile files to the ISY if neccessary or version changed.
        self.poly.updateProfile()

        # Send the default custom parameters documentation file to Polyglot
        self.poly.setCustomParamsDoc()

        # Initializing a heartbeat
        self.heartbeat()

        # Wait for all handlers to finish
        LOGGER.warning("Waiting for all handlers to complete...")
        self.Notices["waiting"] = "Waiting on valid configuration"
        self.all_handlers_st_event.wait(timeout=60)
        if not self.all_handlers_st_event.is_set():
            # start-up failed
            LOGGER.error("Timed out waiting for handlers to startup")
            self.setDriver("ST", 2)  # start-up failed
            self.Notices["error"] = "Error start-up timeout.  Check config & restart"
            return

        # Discover and wait for discovery to complete
        discoverSuccess = self.discover_cmd()

        # first update from Gateway
        if not discoverSuccess:
            # start-up failed
            LOGGER.error(f"First discovery failed!!! exit {self.name}")
            self.Notices["error"] = "Error first discovery.  Check config & restart"
            self.setDriver("ST", 2)
            return

        # Discover and wait for discovery to complete
        mqttSuccess = self._mqtt_start()

        # first update from Gateway
        if not mqttSuccess:
            # start-up failed
            LOGGER.error(f"MQTT connection failed!!! exit {self.name}")
            self.Notices["error"] = "Error MQTT connection.  Check config & restart"
            self.setDriver("ST", 2)
            return

        self.Notices.delete("waiting")
        LOGGER.info("Started MQTT NodeServer v%s", self.poly.serverdata)
        self.query(command=f"{self.name}: STARTUP")

        # signal to the nodes, its ok to start
        self.ready_event.set()

        # clear inital start-up message
        if self.Notices.get("hello"):
            self.Notices.delete("hello")

        LOGGER.info(f"exit {self.name}")

    def _mqtt_start(self):
        """Initialize and connect to the MQTT broker."""
        self.mqtt_bridge = MqttBridge(self)
        return self.mqtt_bridge.start()

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
        address = data.get("address")
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
                self.queue_condition.wait(timeout=0.2)
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
        LOGGER.debug(f"enter: Loading data {data}")
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
        LOGGER.info("parmHandler: Loading parameters now")
        self.Parameters.load(params)
        self.handler_params_st = True
        LOGGER.info("parmHandler Done...")
        self.check_handlers()

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
        LOGGER.debug("Loading typed parameters now")
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
        LOGGER.debug("Loading typed data now")
        if data is None:
            LOGGER.warning("No custom data")
        else:
            self.TypedData.load(data)
        LOGGER.debug(f"Loaded typed data {data}")
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
        if (
            self.handler_params_st
            and self.handler_data_st
            and self.handler_typedparams_st
            and self.handler_typeddata_st
        ):
            self.all_handlers_st_event.set()

    def checkParams(self):
        """Load and validate configuration parameters."""
        has_devfile = bool(self.Parameters.get("devfile"))
        has_devlist = bool(self.Parameters.get("devlist"))

        if not has_devfile and not has_devlist:
            LOGGER.error(
                "checkParams: No devfile or devlist configured! Must be configured."
            )
            return False

        if has_devfile and not self._load_devfile_config():
            return False

        if has_devlist and not self._load_devlist_config():
            return False

        return self._load_mqtt_parameters()

    def _load_devfile_config(self):
        """Load device configuration from YAML file."""
        return config_loader.load_devfile_config(self)

    def _load_devlist_config(self):
        """Load device configuration from JSON string."""
        return config_loader.load_devlist_config(self)

    def upsert_by_id(self, config_list, new_entry):
        """Update or insert device configuration by ID."""
        return config_loader.upsert_by_id(config_list, new_entry)

    def _load_mqtt_parameters(self) -> bool:
        """Load MQTT connection parameters with fallback hierarchy."""
        return config_loader.load_mqtt_parameters(self)

    def _get_str(*args: Optional[Any]) -> Optional[str]:
        """Get the first string value from a list of arguments."""
        return config_loader.get_str(*args)

    def _get_int(*args: Optional[Any]) -> Optional[int]:
        """Get the first integer value from a list of arguments."""
        return config_loader.get_int(*args)

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
        LOGGER.info(f"enter: level={level}")
        if level["level"] < 10:
            LOGGER.info("Setting basic config to DEBUG...")
            LOG_HANDLER.set_basic_config(True, logging.DEBUG)
        else:
            LOGGER.info("Setting basic config to WARNING...")
            LOG_HANDLER.set_basic_config(True, logging.WARNING)
        LOGGER.info(f"exit: level={level}")

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
        if not self.ready_event.is_set():
            LOGGER.debug("Node not ready yet, exiting poll")
            return

        if "shortPoll" in flag:
            LOGGER.debug("longPoll (controller)")
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
        LOGGER.debug("Exit")

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
            LOGGER.info("Discover already running.")
            return success

        self.discovery_in = True
        LOGGER.info("In Discovery...")

        if self.checkParams() and self._discover():
            success = True
            LOGGER.info("Discovery Success")
            if getattr(self, "mqttc", None) and self.mqttc.is_connected():
                self.mqtt_subscribe()
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
            self.setDriver("GV0", self.numNodes)
            success = True
            LOGGER.info(f"Discovery complete. success = {success}")
        except Exception as ex:
            LOGGER.error(f"Discovery Failure: {ex}", exc_info=True)
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
        LOGGER.info("discovery start")
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
        LOGGER.debug(f"DEVLIST: {self.devlist}")

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
        dev["status_topic"] = self._normalize_topic(
            dev["status_topic"], self.status_prefix
        )

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
                dev["extra_status_topic"] = extra_topics[0]
                LOGGER.info(
                    f'Adding EXTRA {dev["extra_status_topic"]} for {dev.get("name", dev["id"])}'
                )
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
            if node not in nodes_new:
                LOGGER.info(f"need to delete node {node}")
                self._remove_status_topics(node)
                self.poly.delNode(node)
                self.discovery_in = False
                LOGGER.info("Done Cleanup")
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
        topics_to_remove = []
        # Collect topics associated with the node to be removed
        for status_topic, device_address in self.status_topics_to_devices.items():
            if device_address == node:
                topics_to_remove.append(status_topic)

        # Remove the collected topics
        if topics_to_remove and self.mqtt_bridge:
            self.mqtt_bridge.unsubscribe(topics_to_remove)

        for status_topic in topics_to_remove:
            if status_topic in self.status_topics:
                self.status_topics.remove(status_topic)
            if status_topic in self.status_topics_to_devices:
                self.status_topics_to_devices.pop(status_topic)
                LOGGER.info(f"Removed subscription for topic: {status_topic}")

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
            LOGGER.info("Poly MQTT Connected")
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
        LOGGER.debug(f"Received message from {topic}: {payload}")

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

    def _process_json_message(
        self, topic: str, payload: str, data: Dict[str, Any]
    ) -> None:
        """Process JSON-formatted MQTT message.

        Args:
            topic (str): MQTT topic of the message.
            payload (str): Raw message payload.
            data (Dict[str, Any]): Parsed JSON data.
        """
        # Extract StatusSNS data if present
        if "StatusSNS" in data:
            data = data["StatusSNS"]
            LOGGER.debug(f"StatusSNS data: {data}")

        # Try to process as sensor data first
        if self._process_sensor_data(topic, payload, data):
            return

        # Process as regular JSON message
        LOGGER.debug(f"Processing JSON message: {payload}")
        self._route_message_to_device(topic, payload)

    def _process_sensor_data(
        self, topic: str, payload: str, data: Dict[str, Any]
    ) -> bool:
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
                    LOGGER.debug(f"{log_prefix}: {sensor}")
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
        if sensor_type == "ANALOG":
            return (
                data[sensor_type]
                if isinstance(data[sensor_type], list)
                else [data[sensor_type]]
            )
        else:
            return [key for key in data.keys() if sensor_type in key]

    def _process_plain_text_message(self, topic: str, payload: str) -> None:
        """Process plain text MQTT message.

        Args:
            topic (str): MQTT topic of the message.
            payload (str): Raw message payload.
        """
        LOGGER.debug(f"Processing plain text message: {payload}")
        self._route_message_to_device(topic, payload)

    def _route_message_to_device(
        self, topic: str, payload: str, sensor: Optional[str] = None
    ) -> None:
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
                node = self.poly.getNode(device_address)
                if node:
                    node.updateInfo(payload, topic)
                else:
                    LOGGER.warning(
                        f"Node object not found for address: {device_address}"
                    )
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
        LOGGER.debug(
            f"STATUS TO DEVICES = {self.status_topics_to_devices.get(topic, None)}"
        )
        return self.status_topics_to_devices.get(topic, None)

    def _get_device_address_from_sensor_id(
        self, topic: str, sensor_type: str
    ) -> Optional[str]:
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
        LOGGER.debug(f"GDA1: topic: {topic}  sensor_type: {sensor_type}")
        LOGGER.debug(f"GDA1b: devlist: {self.devlist}")

        topic_part = topic.rsplit("/")[1]

        # Look for device with matching sensor_id
        for device in self.devlist:
            LOGGER.debug(f"GDA2: device: {device}")
            if (
                "sensor_id" in device
                and topic_part in device["status_topic"]
                and sensor_type in device["sensor_id"]
            ):
                node_id = self._format_device_address(device)
                LOGGER.debug(f"GDA2b: NODE_ID: {node_id}, {topic}, {sensor_type}")
                return node_id

        # Fallback to topic-based lookup
        LOGGER.debug("GDA3: NODE_ID2: None")
        node_id = self._dev_by_topic(topic)
        LOGGER.debug(f"GDA4: revert to topic NODE_ID3: {node_id}")
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
        """Publish a message to an MQTT topic."""
        if self.mqtt_bridge:
            self.mqtt_bridge.publish(topic, message)

    def mqtt_subscribe(self):
        """Subscribe to MQTT status topics."""
        if self.mqtt_bridge:
            self.mqtt_bridge.subscribe()

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
        self.setDriver("ST", 0, report=True, force=True)
        LOGGER.info("bye bye ... deleted.")

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
        self.setDriver("ST", 0, report=True, force=True)
        self.Notices.clear()
        if self.mqtt_bridge:
            self.mqtt_bridge.stop()
        elif self.mqttc:
            self.mqttc.loop_stop()
            self.mqttc.disconnect()
        LOGGER.info("NodeServer stopped.")

    def heartbeat(self):
        """Send heartbeat signal to ISY.

        This function uses the long poll interval to alternately send ON and OFF
        commands back to the ISY. Programs on the ISY can monitor this heartbeat
        to determine if the NodeServer is running properly.

        Returns:
            None
        """
        LOGGER.debug(f"heartbeat: hb={self.hb}")
        command = "DOF" if self.hb else "DON"
        self.reportCmd(command, 2)
        self.hb = not self.hb
        LOGGER.debug("Exit")

    """
    UOMs:
    25: index
    107: Raw 1-byte unsigned value

    Driver controls:
    ST: Status
    GV0: Custom Control 0
    """
    drivers = [
        {"driver": "ST", "value": 1, "uom": 25, "name": "Controller Status"},
        {"driver": "GV0", "value": 0, "uom": 107, "name": "NumberOfNodes"},
    ]

    """
    Commands that this node can handle.
    Should match the 'accepts' section of the nodedef file.
    """
    commands = {
        "DISCOVER": discover_cmd,
        "QUERY": query,
    }
