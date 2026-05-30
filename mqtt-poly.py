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

VERSION = "0.50.3"

# Version history: see CHANGELOG.md

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
