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
import time
from threading import Event, Condition, Lock
from collections import deque
from typing import Dict, List, Optional, Any

# external libraries
from udi_interface import Node, LOGGER, Custom, LOG_HANDLER

# local modules
from . import config_loader
from . import discovery
from .constants import SENSOR_PROCESSORS
from .mqtt_bridge import MqttBridge
from .tasmota_payload import parse_mqtt_json


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
        self._status_topics_lock = Lock()
        self._mqtt_callback_queue: deque = deque()
        self._mqtt_callback_lock = Lock()
        self._mqtt_stopping = False
        self._mqtt_connected_once = False

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
        LOGGER.info("MQTT NodeServer %s", self.poly.serverdata["version"])
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
        self._drain_mqtt_callbacks_for(timeout=10.0)

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
        has_devlist = bool(self.Parameters.get("devlist"))

        if not config_loader.wants_devfile(self) and not has_devlist:
            LOGGER.error(
                "checkParams: No devfile or devlist configured! Must be configured."
            )
            return False

        if config_loader.wants_devfile(self) and not self._load_devfile_config():
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
        self._drain_mqtt_callbacks()

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

        self._drain_mqtt_callbacks()

        self.discovery_in = True
        LOGGER.info("In Discovery...")
        topics_before = set(self.status_topics)

        if self.checkParams() and self._discover():
            success = True
            LOGGER.info("Discovery Success")
            added_topics = [
                topic for topic in self.status_topics if topic not in topics_before
            ]
            if (
                added_topics
                and self.mqtt_bridge
                and self.mqtt_bridge.client
                and self.mqtt_bridge.client.is_connected()
            ):
                self.mqtt_bridge.subscribe(topics=added_topics, query_nodes=False)
        else:
            LOGGER.error("Discovery Failure")
        self.discovery_in = False
        return success

    def _discover(self):
        """Discover devices and manage node lifecycle."""
        return discovery.discover_devices(self)

    def _discover_nodes(self, nodes_existing, nodes_new):
        """Discover and create device nodes."""
        return discovery.discover_nodes(self, nodes_existing, nodes_new)

    def _validate_device_definition(self, dev):
        """Validate device configuration has required fields."""
        return discovery.validate_device_definition(dev)

    def _create_device_node(self, dev, name, address):
        """Create a device node from configuration."""
        return discovery.create_device_node(self, dev, name, address)

    def _add_device_status_topics(self, dev):
        """Add status topics for a device based on its configuration."""
        return discovery.add_device_status_topics(self, dev)

    def _add_status_topics(self, dev, status_topics: List[str]):
        """Add status topics and map them to device address."""
        return discovery.add_status_topics(self, dev, status_topics)

    def _normalize_topic(self, topic: Optional[str], prefix: Optional[str]) -> str:
        """Normalize MQTT topic by replacing placeholder with prefix."""
        return discovery.normalize_topic(topic, prefix)

    def _cleanup_nodes(self, nodes_new, nodes_old):
        """Remove nodes that are no longer in the device list."""
        return discovery.cleanup_nodes(self, nodes_new, nodes_old)

    def _remove_status_topics(self, node):
        """Remove status topics for a deleted node."""
        return discovery.remove_status_topics(self, node)

    def _enqueue_mqtt_callback(self, func, *args, **kwargs) -> None:
        """Queue MQTT callback work for the Polyglot/main thread."""
        with self._mqtt_callback_lock:
            self._mqtt_callback_queue.append((func, args, kwargs))

    def _drain_mqtt_callbacks(self) -> None:
        """Run queued MQTT callback work on the Polyglot/main thread."""
        while True:
            with self._mqtt_callback_lock:
                if not self._mqtt_callback_queue:
                    break
                func, args, kwargs = self._mqtt_callback_queue.popleft()
            try:
                func(*args, **kwargs)
            except Exception:
                LOGGER.exception("Error running deferred MQTT callback")

    def _drain_mqtt_callbacks_for(
        self, timeout: float = 10.0, interval: float = 0.05
    ) -> None:
        """Drain MQTT callbacks until connected or timeout (startup / broker wait)."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self._drain_mqtt_callbacks()
            if self._mqtt_connected_once:
                return
            time.sleep(interval)
        self._drain_mqtt_callbacks()

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
        if self._mqtt_stopping:
            return
        self._enqueue_mqtt_callback(self._handle_mqtt_connect, rc)

    def _handle_mqtt_connect(self, rc: int) -> None:
        """Apply connect results on the Polyglot/main thread."""
        if self._mqtt_stopping:
            return
        if rc == 0:
            LOGGER.info("Poly MQTT connected/reconnected")
            if self.Notices.get("mqtt"):
                self.Notices.delete("mqtt")
            is_reconnect = self._mqtt_connected_once
            self._mqtt_connected_once = True
            if self.mqtt_bridge:
                self.mqtt_bridge.subscribe(query_nodes=not is_reconnect)
        else:
            LOGGER.error(f"Poly MQTT Connect failed with rc:{rc}")
            self.Notices["mqtt"] = (
                f"User MQTT connection failed (rc {rc}); "
                "retrying automatically"
            )

    def _on_connect_fail(self, _mqttc, _userdata):
        """Handle MQTT TCP connection failures before CONNACK."""
        if self._mqtt_stopping:
            return
        self._enqueue_mqtt_callback(self._handle_mqtt_connect_fail)

    def _handle_mqtt_connect_fail(self) -> None:
        """Log TCP connect failures on the Polyglot/main thread."""
        if self._mqtt_stopping:
            return
        LOGGER.warning("Poly MQTT TCP connection failed; retrying automatically")
        self.Notices["mqtt"] = (
            "Waiting on user MQTT connection; retrying automatically"
        )

    def _on_disconnect(self, _mqttc, _userdata, rc):
        """Handle MQTT disconnection events.

        This method is called when the MQTT client disconnects from the broker.
        It handles both graceful disconnections and unexpected disconnections.
        Paho's automatic reconnect handles unexpected disconnections.

        Args:
            _mqttc: MQTT client instance (unused).
            _userdata: User data passed to the client (unused).
            rc (int): Return code indicating disconnection reason (0 = graceful).

        Returns:
            None
        """
        if self._mqtt_stopping:
            return
        self._enqueue_mqtt_callback(self._handle_mqtt_disconnect, rc)

    def _handle_mqtt_disconnect(self, rc: int) -> None:
        """Apply disconnect notices on the Polyglot/main thread."""
        if self._mqtt_stopping:
            return
        if rc != 0:
            LOGGER.warning(
                "Poly MQTT disconnected (rc %s); "
                "Paho will retry automatically",
                rc,
            )
            self.Notices["mqtt"] = (
                "User MQTT disconnected; retrying automatically"
            )
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
        """Parse JSON payload and unwrap Tasmota StatusSNS envelopes."""
        return parse_mqtt_json(payload)

    def _process_json_message(
        self, topic: str, payload: str, data: Dict[str, Any]
    ) -> None:
        """Process JSON-formatted MQTT message."""
        normalized_payload = json.dumps(data, separators=(",", ":"))

        if self._process_sensor_data(topic, normalized_payload, data):
            return

        LOGGER.debug(f"Processing JSON message: {normalized_payload}")
        self._route_message_to_device(topic, normalized_payload)

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
        """Format device address for ISY compatibility."""
        return discovery.format_device_address(self, dev)

    def mqtt_pub(self, topic, message):
        """Publish a message to an MQTT topic."""
        if not self.mqtt_bridge:
            LOGGER.warning("MQTT publish rejected: bridge not initialized")
            return False
        if not self.mqtt_bridge.publish(topic, message):
            LOGGER.warning("MQTT publish failed: topic=%s", topic)
            return False
        return True

    def mqtt_subscribe(self, query_nodes=True):
        """Subscribe to MQTT status topics."""
        if self.mqtt_bridge:
            return self.mqtt_bridge.subscribe(query_nodes=query_nodes)
        return False

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
        self._mqtt_stopping = True
        with self._mqtt_callback_lock:
            self._mqtt_callback_queue.clear()
        self.setDriver("ST", 0, report=True, force=True)
        self.Notices.clear()
        if self.mqtt_bridge:
            self.mqtt_bridge.stop()
        elif self.mqttc:
            self.mqttc.loop_stop()
            self.mqttc.disconnect()
            self.mqttc = None
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
