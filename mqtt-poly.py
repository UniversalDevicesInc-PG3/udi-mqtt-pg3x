#!/usr/bin/env python3
"""
This is a Plugin/NodeServer for Polyglot v3 written in Python3
modified from v3 template version by (Bob Paauwe) bpaauwe@yahoo.com
It is a plugin to interface an MQTT server and Polyglot for EISY/Polisy

udi-mqtt-pg3 NodeServer/Plugin for EISY/Polisy

(c) 2025 Stephen Jenkins
"""

# std libraries
import sys

# external libraries
import udi_interface

# local imports
from nodes import Controller

LOGGER = udi_interface.LOGGER

VERSION = "0.50.0"

"""
0.50.0
DONE refactor Controller/Nodes for Pythonic & commenting
DONE add user defined default status_prefix & cmd_prefix
DONE add numofnodes
DONE add MQDroplet device

0.40.3
DONE: fixed typos in POLYGLOT_CONFIG.md
STARTED: Organize device types according to Tasmota, Sensor etc.
TODO: Reorganize sample devfile for clarity and comments

0.40.2
DONE README.md clean-up
DONE POLYGLOT_CONFIG.md clean-up

0.40.1
DONE s31 displays in program

0.40.0
DONE change numbering to allow for branch management
DONE raw fix docs & allow int in addition to str
DONE find topic by topic if no device_id find
DONE:discover button updates nodes and MQTT subscriptions
DONE config.md fixes
DONE status for switch device available in programs
DONE internal: improve logging for debug
DONE:   Changed versioning so git branches and hot fixes can work.
          so 0.40.0 means it will be on branch 0.40 with the last .0
          reserved for hotfixes.  These will then be pushed by PG3 to users
DONE:   Switch make Status available in IF for programs
DONE:   Parameters are not initially populated, plugin uses the following defaults:
           mqtt_server = LocalHost
           mqtt_port = 1884
           mutt-user = admin (same as None)
           mqtt_password = admin (same as None)
DONE:   'raw' fix docs and allow to take int type in addition to str
DONE:   discover button updates nodes and MQTT subscriptions
DONE:   internal: improve logging for debug
DONE:   S31 debug: displays in program now *** need to know it works

Previous versions:

0.0.39
DEBUG discover bug fix

0.0.38
DONE change node throttling timer from 0.1s to 0.2s

0.0.37
DONE re-factor files separating controller and nodes
DONE fix adding & removal of nodes during start-up and/or discovery

"""

if __name__ == "__main__":
    polyglot = None
    try:
        """
        Instantiates the Interface to Polyglot.

        * Optionally pass list of class names
          - PG2 had the controller node name here
        """
        polyglot = udi_interface.Interface([])
        """
        Starts MQTT and connects to Polyglot.
        """
        polyglot.start(VERSION)
        polyglot.updateProfile()

        """
        Creates the Controller Node and passes in the Interface, the node's
        parent address, node's address, and name/title

        * address, parent address, and name/title are new for Polyglot
          version 3
        * use 'controller' for both parent and address and PG3 will be able
          to automatically update node server status
        """
        control = Controller(polyglot, "mqctrl", "mqctrl", "MQTT")

        """
        Sits around and does nothing forever, keeping your program running.

        * runForever() moved from controller class to interface class in
          Polyglot version 3
        """
        polyglot.runForever()
    except (KeyboardInterrupt, SystemExit):
        LOGGER.warning("Received interrupt or exit...")
        """
        Catch SIGTERM or Control-C and exit cleanly.
        """
        if polyglot is not None:
            polyglot.stop()
    except Exception as err:
        LOGGER.error("Exception: {0}".format(err), exc_info=True)
    sys.exit(0)
