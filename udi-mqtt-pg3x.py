#!/usr/bin/env python3
"""MQTT NodeServer for Polyglot V3 on EISY/Polisy.

Interface between an MQTT broker and Polyglot.

(c) 2025 Stephen Jenkins

Version history: see CHANGELOG.md
"""

import sys

import udi_interface

from nodes import Controller

VERSION = "0.50.9"

if __name__ == "__main__":
    polyglot = None
    try:
        polyglot = udi_interface.Interface([])
        polyglot.start(VERSION)
        Controller(polyglot, "mqctrl", "mqctrl", "MQTT")
        polyglot.runForever()
    except (KeyboardInterrupt, SystemExit):
        udi_interface.LOGGER.warning("Received interrupt or exit...")
        if polyglot is not None:
            polyglot.stop()
    except Exception:
        udi_interface.LOGGER.error("Fatal error starting plugin", exc_info=True)
    sys.exit(0)
