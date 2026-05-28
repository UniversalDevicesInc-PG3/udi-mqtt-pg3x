"""Tests for Tasmota MQTT payload normalization."""

import json

from nodes.tasmota_payload import parse_mqtt_json, unwrap_status_sns


class TestUnwrapStatusSns:
    def test_unwraps_status_sns(self):
        data = {"Time": "2025-01-01", "StatusSNS": {"DS18B20-1": {"Temperature": 72.0}}}
        assert unwrap_status_sns(data) == {"DS18B20-1": {"Temperature": 72.0}}

    def test_passthrough_without_wrapper(self):
        data = {"POWER": "ON"}
        assert unwrap_status_sns(data) == data


class TestParseMqttJson:
    def test_parse_wrapped_payload(self):
        payload = json.dumps(
            {"Time": "2025-01-01", "StatusSNS": {"BME280": {"Temperature": 25.0}}}
        )
        assert parse_mqtt_json(payload) == {"BME280": {"Temperature": 25.0}}

    def test_parse_plain_payload(self):
        payload = json.dumps({"POWER": "ON", "Dimmer": 50})
        assert parse_mqtt_json(payload) == {"POWER": "ON", "Dimmer": 50}

    def test_invalid_json_returns_none(self):
        assert parse_mqtt_json("not-json") is None
