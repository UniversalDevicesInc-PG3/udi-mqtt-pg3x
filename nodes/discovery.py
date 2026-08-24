"""Device discovery and MQTT topic registration."""

import json
from typing import List, Optional

from udi_interface import LOGGER

from .device_registry import DEVICE_CONFIG


def format_device_address(controller, dev) -> str:
    """Format device address for ISY compatibility."""
    name = dev["id"].replace("_", "").replace("-", "_")
    return controller.poly.getValidAddress(name)


def normalize_topic(topic: Optional[str], prefix: Optional[str]) -> str:
    """Replace leading '~' in a topic with the configured prefix."""
    if topic is None:
        return ""
    if topic.startswith("~") and prefix is not None:
        return prefix + topic[1:]
    return topic


def validate_device_definition(dev) -> bool:
    """Validate device configuration has required fields."""
    required_fields = ["id", "status_topic", "cmd_topic", "type"]
    if not all(field in dev for field in required_fields):
        LOGGER.error(f"Invalid device definition: {json.dumps(dev)}")
        return False
    return True


def add_status_topics(controller, dev, status_topics: List[str]) -> None:
    """Add status topics and map them to a device address."""
    device_address = format_device_address(controller, dev)

    with controller._status_topics_lock:
        for raw_topic in status_topics:
            status_topic = normalize_topic(raw_topic, controller.status_prefix)
            if status_topic in controller.status_topics_to_devices:
                existing = controller.status_topics_to_devices[status_topic]
                if existing != device_address:
                    LOGGER.warning(
                        "Topic %s already mapped to %s; keeping existing mapping",
                        status_topic,
                        existing,
                    )
                continue

            if status_topic not in controller.status_topics:
                controller.status_topics.append(status_topic)
            controller.status_topics_to_devices[status_topic] = device_address


def add_device_status_topics(controller, dev) -> None:
    """Add status topics for a device based on its type configuration."""
    device_type = dev["type"]
    device_config = DEVICE_CONFIG.get(device_type, {})

    if "status_topics" in device_config:
        status_topics = device_config["status_topics"](dev)
        add_status_topics(controller, dev, status_topics)
    else:
        add_status_topics(controller, dev, [dev["status_topic"]])

    if "extra_status_topics" in device_config:
        extra_topics = device_config["extra_status_topics"](dev)
        if extra_topics:
            dev["extra_status_topic"] = extra_topics[0]
            LOGGER.info(
                f'Adding EXTRA {dev["extra_status_topic"]} for {dev.get("name", dev["id"])}'
            )
        add_status_topics(controller, dev, extra_topics)


def create_device_node(controller, dev, name, address) -> bool:
    """Create a device node from configuration."""
    device_type = dev["type"]

    if device_type not in DEVICE_CONFIG:
        LOGGER.error(f"Device type {device_type} is not yet supported")
        return False

    device_config = DEVICE_CONFIG[device_type]
    node_class = device_config["node_class"]

    dev["status_topic"] = normalize_topic(dev["status_topic"], controller.status_prefix)
    dev["cmd_topic"] = normalize_topic(dev["cmd_topic"], controller.cmd_prefix)
    add_device_status_topics(controller, dev)

    LOGGER.info(f"Adding {device_type}, {name}")
    controller.poly.addNode(node_class(controller.poly, controller.address, address, name, dev))
    return True


def discover_nodes(controller, nodes_existing, nodes_new) -> None:
    """Discover and create device nodes."""
    LOGGER.info("discovery start")
    controller.discovery_in = True
    for dev in controller.devlist:
        if not validate_device_definition(dev):
            continue

        name = dev.get("name", dev["id"])
        address = format_device_address(controller, dev)

        if address not in nodes_existing:
            if not create_device_node(controller, dev, name, address):
                continue
            controller.wait_for_node_done()
        nodes_new.append(address)
    LOGGER.info("Done adding nodes.")
    LOGGER.debug(f"DEVLIST: {controller.devlist}")


def remove_status_topics(controller, node) -> None:
    """Remove status topics associated with a deleted node."""
    with controller._status_topics_lock:
        topics_to_remove = [
            status_topic
            for status_topic, device_address in controller.status_topics_to_devices.items()
            if device_address == node
        ]

        if topics_to_remove and controller.mqtt_bridge:
            controller.mqtt_bridge.unsubscribe(topics_to_remove)

        for status_topic in topics_to_remove:
            if status_topic in controller.status_topics:
                controller.status_topics.remove(status_topic)
            if status_topic in controller.status_topics_to_devices:
                controller.status_topics_to_devices.pop(status_topic)
                LOGGER.info(f"Removed subscription for topic: {status_topic}")


def cleanup_nodes(controller, nodes_new, nodes_old) -> bool:
    """Remove nodes that are no longer in the device list."""
    for node in nodes_old:
        if node not in nodes_new:
            LOGGER.info(f"need to delete node {node}")
            controller._remove_status_topics(node)
            controller.poly.delNode(node)
            controller.discovery_in = False
            LOGGER.info("Done Cleanup")
    return True


def discover_devices(controller) -> bool:
    """Discover devices and manage node lifecycle."""
    success = False
    nodes_existing = controller.poly.getNodes()
    LOGGER.debug(f"current nodes = {nodes_existing}")
    nodes_old = [node for node in nodes_existing if node != controller.id]
    nodes_new = []

    try:
        discover_nodes(controller, nodes_existing, nodes_new)
        cleanup_nodes(controller, nodes_new, nodes_old)
        controller.numNodes = len(nodes_new)
        controller.setDriver("GV0", controller.numNodes)
        success = True
        LOGGER.info(f"Discovery complete. success = {success}")
    except Exception as ex:
        LOGGER.error(f"Discovery Failure: {ex}", exc_info=True)
    return success
