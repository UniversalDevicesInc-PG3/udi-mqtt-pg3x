"""Load and validate MQTT device configuration from Polyglot parameters."""

import json
from pathlib import Path
from typing import Any, List, Optional

import yaml
from udi_interface import LOGGER

from .constants import DEFAULT_CONFIG

DEFAULT_DEVFILE = "data/mqtt-devices.yaml"


def get_str(*args: Optional[Any]) -> Optional[str]:
    """Return the first string argument, or None."""
    for val in args:
        if isinstance(val, str):
            return val
    return None


def get_int(*args: Optional[Any]) -> Optional[int]:
    """Return the first int argument, or the first numeric string as int."""
    for val in args:
        if isinstance(val, int):
            return val
        if isinstance(val, str) and val.isdigit():
            return int(val)
    return None


def upsert_by_id(config_list: List[dict], new_entry: dict) -> None:
    """Update or append a device entry keyed by ``id``."""
    new_id = new_entry.get("id")
    for i, entry in enumerate(config_list):
        if entry.get("id") == new_id:
            config_list[i] = new_entry
            return
    config_list.append(new_entry)


def resolve_devfile_path(filename: str) -> Path:
    """Resolve devfile parameter to a path under the node server install folder."""
    path = Path(filename.strip())
    if path.is_absolute():
        return path
    if len(path.parts) == 1:
        return Path("data") / path.name
    return path


def wants_devfile(controller) -> bool:
    """Return True when a devfile should be loaded (explicit path or default)."""
    raw = controller.Parameters.get("devfile")
    if isinstance(raw, str) and raw.strip():
        return True
    return not bool(controller.Parameters.get("devlist"))


def load_devfile_config(controller) -> bool:
    """Load devices and general settings from a YAML devfile."""
    raw = controller.Parameters.get("devfile", "")
    if not isinstance(raw, str) or not raw.strip():
        devfile_path = resolve_devfile_path(DEFAULT_DEVFILE)
    else:
        devfile_path = resolve_devfile_path(raw)

    try:
        with open(devfile_path, "r", encoding="utf-8") as file:
            dev_yaml = yaml.safe_load(file)
    except (OSError, yaml.YAMLError) as ex:
        error_type = "open" if isinstance(ex, OSError) else "parse"
        LOGGER.error(f"Failed to {error_type} {devfile_path}: {ex}")
        return False

    if "devices" not in dev_yaml:
        LOGGER.error(
            f"Manual discovery file {devfile_path} is missing devices section"
        )
        return False

    devices = dev_yaml.get("devices")
    general = dev_yaml.get("general", [])
    LOGGER.info(f"devices = {devices}")
    LOGGER.info(f"general = {general}")

    controller.devlist = devices
    controller.general = {k: v for d in general for k, v in d.items()}
    return True


def load_devlist_config(controller) -> bool:
    """Load or merge devices from a JSON devlist parameter."""
    devlist_data = controller.Parameters["devlist"]
    if not devlist_data:
        LOGGER.error("No devlist data provided")
        return False

    try:
        if isinstance(devlist_data, str):
            parsed_data = json.loads(devlist_data)
        else:
            parsed_data = devlist_data

        if isinstance(parsed_data, list):
            for entry in parsed_data:
                if not isinstance(entry, dict):
                    LOGGER.error("Devlist entries must be device dictionaries")
                    return False
                upsert_by_id(controller.devlist, entry)
        elif isinstance(parsed_data, dict):
            upsert_by_id(controller.devlist, parsed_data)
        else:
            LOGGER.error("Devlist data must be a list or dictionary")
            return False
    except (json.JSONDecodeError, TypeError) as ex:
        LOGGER.error(f"Failed to parse devlist: {ex}")
        return False
    return True


def load_mqtt_parameters(controller) -> bool:
    """Load MQTT broker settings using Parameters, devfile, then defaults."""
    try:
        controller.mqtt_server = get_str(
            controller.Parameters.get("mqtt_server"),
            controller.general.get("mqtt_server"),
            DEFAULT_CONFIG.get("mqtt_server"),
        )
        controller.mqtt_port = get_int(
            controller.Parameters.get("mqtt_port"),
            controller.general.get("mqtt_port"),
            DEFAULT_CONFIG.get("mqtt_port"),
        )
        controller.mqtt_user = get_str(
            controller.Parameters.get("mqtt_user"),
            controller.general.get("mqtt_user"),
            DEFAULT_CONFIG.get("mqtt_user"),
        )
        controller.mqtt_password = get_str(
            controller.Parameters.get("mqtt_password"),
            controller.general.get("mqtt_password"),
            DEFAULT_CONFIG.get("mqtt_password"),
        )
        controller.status_prefix = get_str(
            controller.Parameters.get("status_prefix"),
            controller.general.get("status_prefix"),
        )
        controller.cmd_prefix = get_str(
            controller.Parameters.get("cmd_prefix"),
            controller.general.get("cmd_prefix"),
        )

        if controller.mqtt_server is None or controller.mqtt_port is None:
            raise ValueError("MQTT server and port must be configured.")
    except (ValueError, TypeError) as ex:
        LOGGER.error(f"Failed to parse MQTT parameters: {ex}")
        return False
    return True


def check_params(controller) -> bool:
    """Load devfile and/or devlist configuration and MQTT broker settings."""
    has_devlist = bool(controller.Parameters.get("devlist"))

    if not wants_devfile(controller) and not has_devlist:
        LOGGER.error(
            "checkParams: No devfile or devlist configured! Must be configured."
        )
        return False

    if wants_devfile(controller) and not load_devfile_config(controller):
        return False

    if has_devlist and not load_devlist_config(controller):
        return False

    return load_mqtt_parameters(controller)
