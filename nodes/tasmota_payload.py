"""Tasmota MQTT JSON payload parsing helpers."""

import json
from typing import Any, Dict, Optional


def unwrap_status_sns(data: Dict[str, Any]) -> Dict[str, Any]:
    """Return the inner StatusSNS object when present."""
    if "StatusSNS" in data:
        return data["StatusSNS"]
    return data


def parse_mqtt_json(payload: str) -> Optional[Dict[str, Any]]:
    """Parse MQTT JSON and unwrap Tasmota StatusSNS envelopes."""
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return None

    if not isinstance(data, dict):
        return None

    return unwrap_status_sns(data)
