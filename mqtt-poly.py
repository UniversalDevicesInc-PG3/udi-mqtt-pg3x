#!/usr/bin/env python3
"""
This is a Plugin/NodeServer for Polyglot v3 written in Python3
modified from v3 template version by (Bob Paauwe) bpaauwe@yahoo.com
It is an interface between HunterDouglas Shades and Polyglot for EISY/Polisy

(c) 2024 Stephen Jenkins
"""
import udi_interface
import sys

LOGGER = udi_interface.LOGGER

VERSION = '0.40.0'

"""
0.40.0
DONE change numbering to allow for branch management
DONE raw fix docs & allow int in addition to str
DONE find topic by topic if no device_id find
DONE:discover button updates nodes and MQTT subscriptions
FIXME config.md fixes
FIXME status for switch device available in programs
STARTED internal: improve logging for debug

Current TODO list from forum:

As the title suggests, please add your bugs, suggestions, and improvement thoughts here. 
I will update this post as ideas make the list and are prioritized.

*** Putting up into Beta under MQTT-poly for the brave to try out and give feedback.

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
DONE:discover button updates nodes and MQTT subscriptions

STARTED:CONFIG.MD, changed references of power to POWER. (please feel free to suggest other improvements to the docs)
STARTED:internal: improve logging for debug

NEXT:   Query is not consistent across the devices

HELP:   S31 debug:  ****need some specifics here of what is happening, logs aways help
HELP:   iFan debug: ****need some specifics here of what is happening, logs aways help
HELP:   Tasmota potential automation opportunities in discovery
HELP:   Multiple-Analog clean-up (particular issues?)
HELP:    Google Assistant is not reporting device status consistently: it shows correctly for a few seconds and then goes to 'OFF' (All / some devices?)

LATER:  simplify devlist/devfile by using 'defaults' for status_topic and cmd_topic. (They are mostly a combination of 'id' and a set of repetitive strings). This could reduce configuration pain by 80% and typos by 90%. Minimum need: 'id:' and 'type:' optional 'name:'


Previous versions:

0.0.39
DEBUG discover bug fix

0.0.38
DONE change node throttling timer from 0.1s to 0.2s

0.0.37
DONE re-factor files separating controller and nodes
DONE fix adding & removal of nodes during start-up and/or discovery

"""

from nodes import Controller

if __name__ == "__main__":
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

        """
        Creates the Controller Node and passes in the Interface, the node's
        parent address, node's address, and name/title

        * address, parent address, and name/title are new for Polyglot
          version 3
        * use 'controller' for both parent and address and PG3 will be able
          to automatically update node server status
        """
        control = Controller(polyglot, 'mqctrl', 'mqctrl', 'MQTT')

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
        polyglot.stop()
    except Exception as err:
        LOGGER.error('Excption: {0}'.format(err), exc_info=True)
    sys.exit(0)




