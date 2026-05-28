"""Pytest fixtures shared across the mqtt-poly test suite.

Polyglot's udi_interface package only re-exports Node/Custom when PG3 startup
succeeds. In local/CI environments that export is missing, so tests patch the
package before node modules import from udi_interface.
"""

import udi_interface
from udi_interface.custom import Custom
from udi_interface.node import Node
from udi_interface.polylogger import LOG_HANDLER, LOGGER

udi_interface.Node = Node
udi_interface.Custom = Custom
udi_interface.LOG_HANDLER = LOG_HANDLER
udi_interface.LOGGER = LOGGER
