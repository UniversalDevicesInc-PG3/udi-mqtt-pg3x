"""
Regression tests for legacy user configuration and install compatibility.

These tests guard documented devfile/devlist formats, device type strings,
and address formatting so refactors do not break existing EISY deployments.
"""

import json

import pytest
import yaml
from unittest.mock import Mock

from nodes.Controller import Controller, DEFAULT_CONFIG, DEVICE_CONFIG


@pytest.fixture
def controller():
    """Minimal Controller instance for config tests."""
    poly = Mock()
    poly.subscribe = Mock()
    poly.ready = Mock()
    poly.addNode = Mock()
    poly.db_getNodeDrivers = Mock(return_value=[])
    poly.getValidAddress = Mock(side_effect=lambda name: name.lower()[:14])
    for attr in [
        "START",
        "POLL",
        "LOGLEVEL",
        "CUSTOMPARAMS",
        "CUSTOMDATA",
        "STOP",
        "DISCOVER",
        "CUSTOMTYPEDDATA",
        "CUSTOMTYPEDPARAMS",
        "ADDNODEDONE",
    ]:
        setattr(poly, attr, attr)
    return Controller(poly, "controller", "controller", "MQTT")


class TestLegacyDevlistFormats:
    """Documented and legacy devlist JSON formats must keep working."""

    def test_devlist_json_array_documented_format(self, controller):
        """POLYGLOT_CONFIG.md array-of-devices format."""
        controller.Parameters = {
            "devlist": json.dumps(
                [
                    {
                        "id": "sonoff1",
                        "type": "switch",
                        "status_topic": "stat/sonoff1/POWER",
                        "cmd_topic": "cmnd/sonoff1/power",
                    },
                    {
                        "id": "sonoff2",
                        "type": "switch",
                        "status_topic": "stat/sonoff2/POWER",
                        "cmd_topic": "cmnd/sonoff2/power",
                    },
                ]
            )
        }

        assert controller._load_devlist_config() is True
        assert len(controller.devlist) == 2
        assert controller.devlist[0]["id"] == "sonoff1"
        assert controller.devlist[1]["id"] == "sonoff2"

    def test_devlist_single_dict_legacy_upsert(self, controller):
        """Legacy single-device dict upsert still works."""
        controller.devlist = [
            {
                "id": "sonoff1",
                "type": "switch",
                "status_topic": "stat/sonoff1/POWER",
                "cmd_topic": "cmnd/sonoff1/power",
            }
        ]
        controller.Parameters = {
            "devlist": json.dumps(
                {
                    "id": "sonoff1",
                    "type": "switch",
                    "status_topic": "stat/sonoff1/POWER2",
                    "cmd_topic": "cmnd/sonoff1/power2",
                }
            )
        }

        assert controller._load_devlist_config() is True
        assert len(controller.devlist) == 1
        assert controller.devlist[0]["status_topic"] == "stat/sonoff1/POWER2"

    def test_devlist_only_loads_mqtt_defaults(self, controller):
        """devlist-only installs must not require devfile general section."""
        controller.Parameters = {
            "devlist": json.dumps(
                [
                    {
                        "id": "sonoff1",
                        "type": "switch",
                        "status_topic": "stat/sonoff1/POWER",
                        "cmd_topic": "cmnd/sonoff1/power",
                    }
                ]
            )
        }

        assert controller.checkParams() is True
        assert controller.mqtt_server == DEFAULT_CONFIG["mqtt_server"]
        assert controller.mqtt_port == DEFAULT_CONFIG["mqtt_port"]

    def test_devfile_and_devlist_merge(self, controller, tmp_path):
        """Documented devfile + devlist overlay behavior."""
        devfile = tmp_path / "devices.yaml"
        devfile.write_text(
            yaml.safe_dump(
                {
                    "general": [{"mqtt_server": "broker.local", "mqtt_port": 1883}],
                    "devices": [
                        {
                            "id": "from_file",
                            "type": "switch",
                            "status_topic": "stat/from_file/POWER",
                            "cmd_topic": "cmnd/from_file/power",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        controller.Parameters = {
            "devfile": str(devfile),
            "devlist": json.dumps(
                [
                    {
                        "id": "from_params",
                        "type": "switch",
                        "status_topic": "stat/from_params/POWER",
                        "cmd_topic": "cmnd/from_params/power",
                    }
                ]
            ),
        }

        assert controller.checkParams() is True
        assert controller.mqtt_server == "broker.local"
        assert controller.mqtt_port == 1883
        ids = {dev["id"] for dev in controller.devlist}
        assert ids == {"from_file", "from_params"}


class TestLegacyDeviceTypes:
    """User-facing device type strings are a configuration contract."""

    @pytest.mark.parametrize(
        "device_type",
        [
            "switch",
            "dimmer",
            "ifan",
            "sensor",
            "flag",
            "TempHumid",
            "Temp",
            "TempHumidPress",
            "distance",
            "shellyflood",
            "analog",
            "s31",
            "raw",
            "RGBW",
            "ratgdo",
            "droplet",
        ],
    )
    def test_documented_device_type_registered(self, device_type):
        assert device_type in DEVICE_CONFIG

    def test_device_address_format_unchanged(self, controller):
        """Address derivation must stay compatible with existing ISY nodes."""
        dev = {"id": "my-switch_01"}
        controller.poly.getValidAddress = Mock(return_value="my_switch01")
        address = controller._format_device_address(dev)
        controller.poly.getValidAddress.assert_called_once_with("my_switch01")
        assert address == "my_switch01"


class TestLegacyStartupAndRouting:
    """Startup gates and routing must not regress for live installs."""

    def test_parameter_handler_unblocks_startup(self, controller):
        controller.handler_data_st = True
        controller.handler_typedparams_st = True
        controller.handler_typeddata_st = True
        controller.handler_params_st = None

        controller.parameterHandler({"devlist": "[]"})

        assert controller.handler_params_st is True
        assert controller.all_handlers_st_event.is_set()

    def test_poll_skips_heartbeat_until_ready(self, controller):
        controller.reportCmd = Mock()
        controller.poll({"shortPoll": True})
        controller.reportCmd.assert_not_called()

    def test_sensor_routing_uses_two_arg_update_info(self, controller):
        node = Mock()
        controller.poly.getNode = Mock(return_value=node)
        controller.devlist = [
            {
                "id": "WemosT1",
                "type": "Temp",
                "sensor_id": "DS18B20-1",
                "status_topic": "tele/Wemos32/SENSOR",
                "cmd_topic": "cmnd/Wemos32",
            }
        ]
        topic = "tele/Wemos32/SENSOR"
        payload = '{"DS18B20-1":{"Temperature":72.5}}'

        controller._route_message_to_device(topic, payload, sensor="DS18B20-1")

        node.updateInfo.assert_called_once_with(payload, topic)

    def test_discover_resubscribes_when_mqtt_connected(self, controller):
        controller.checkParams = Mock(return_value=True)
        controller._discover = Mock(return_value=True)
        controller.mqtt_subscribe = Mock()
        controller.mqttc = Mock()
        controller.mqttc.is_connected.return_value = True

        assert controller.discover_cmd("DISCOVER") is True
        controller.mqtt_subscribe.assert_called_once()
