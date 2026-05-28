"""Shared constants for the MQTT NodeServer."""

DEFAULT_CONFIG = {
    "mqtt_server": "localhost",
    "mqtt_port": 1884,
    "mqtt_user": "admin",
    "mqtt_password": "admin",
    "status_prefix": None,
    "cmd_prefix": None,
}

MQTT_CONNECT_WAIT_SEC = 60

STATUS_TOPIC_PREFIX = "stat/"
TELE_TOPIC_PREFIX = "tele/"
RESULT_TOPIC_SUFFIX = "/RESULT"
STATUS10_TOPIC_SUFFIX = "/STATUS10"

# Sensor processor mapping for MQTT message processing
SENSOR_PROCESSORS = {
    "ANALOG": "_OA",
    "DS18B20": "_ODS",
    "AM2301": "_OAM",
    "BME280": "_OBM",
}
