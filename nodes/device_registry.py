"""Device type registry mapping configuration types to node classes."""

from .MQAnalog import MQAnalog
from .MQbme import MQbme
from .MQDimmer import MQDimmer
from .MQdht import MQdht
from .MQDroplet import MQDroplet
from .MQds import MQds
from .MQFan import MQFan
from .MQFlag import MQFlag
from .MQhcsr import MQhcsr
from .MQratgdo import MQratgdo
from .MQraw import MQraw
from .MQRGBWstrip import MQRGBWstrip
from .MQs31 import MQs31
from .MQSensor import MQSensor
from .MQShellyFlood import MQShellyFlood
from .MQSwitch import MQSwitch
from .constants import (
    RESULT_TOPIC_SUFFIX,
    STATUS10_TOPIC_SUFFIX,
    STATUS_TOPIC_PREFIX,
    TELE_TOPIC_PREFIX,
)

DEVICE_CONFIG = {
    "switch": {
        "node_class": MQSwitch,
    },
    "dimmer": {
        "node_class": MQDimmer,
        "extra_status_topics": lambda dev: [
            dev["status_topic"].rsplit("/", 1)[0] + RESULT_TOPIC_SUFFIX
        ],
    },
    "ifan": {
        "node_class": MQFan,
    },
    "sensor": {
        "node_class": MQSensor,
    },
    "flag": {
        "node_class": MQFlag,
    },
    "TempHumid": {
        "node_class": MQdht,
        "extra_status_topics": lambda dev: [
            dev["status_topic"].rsplit("/", 1)[0]
            + STATUS10_TOPIC_SUFFIX.replace(TELE_TOPIC_PREFIX, STATUS_TOPIC_PREFIX)
        ],
    },
    "Temp": {
        "node_class": MQds,
        "extra_status_topics": lambda dev: [
            dev["status_topic"].rsplit("/", 1)[0]
            + STATUS10_TOPIC_SUFFIX.replace(TELE_TOPIC_PREFIX, STATUS_TOPIC_PREFIX)
        ],
    },
    "TempHumidPress": {
        "node_class": MQbme,
        "extra_status_topics": lambda dev: [
            dev["status_topic"].rsplit("/", 1)[0]
            + STATUS10_TOPIC_SUFFIX.replace(TELE_TOPIC_PREFIX, STATUS_TOPIC_PREFIX)
        ],
    },
    "distance": {
        "node_class": MQhcsr,
    },
    "shellyflood": {
        "node_class": MQShellyFlood,
        "status_topics": lambda dev: (
            dev["status_topic"]
            if isinstance(dev["status_topic"], list)
            else [dev["status_topic"]]
        ),
    },
    "analog": {
        "node_class": MQAnalog,
        "extra_status_topics": lambda dev: [
            dev["status_topic"].rsplit("/", 1)[0]
            + STATUS10_TOPIC_SUFFIX.replace(TELE_TOPIC_PREFIX, STATUS_TOPIC_PREFIX)
        ],
    },
    "s31": {
        "node_class": MQs31,
    },
    "raw": {
        "node_class": MQraw,
    },
    "RGBW": {
        "node_class": MQRGBWstrip,
    },
    "ratgdo": {
        "node_class": MQratgdo,
        "status_topics": lambda dev: [
            dev["status_topic"] + "/status/availability",
            dev["status_topic"] + "/status/light",
            dev["status_topic"] + "/status/door",
            dev["status_topic"] + "/status/motion",
            dev["status_topic"] + "/status/lock",
            dev["status_topic"] + "/status/obstruction",
        ],
    },
    "droplet": {
        "node_class": MQDroplet,
        "status_topics": lambda dev: [
            dev["status_topic"] + "/state",
            dev["status_topic"] + "/health",
        ],
    },
}
