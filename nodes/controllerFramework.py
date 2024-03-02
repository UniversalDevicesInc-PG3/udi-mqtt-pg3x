"""
udi-framework-pg3 NodeServer/Plugin for EISY/PolISY

(C) 2024

controllerFramework
"""

import udi_interface

# Nodes
from nodes import NodeFramework

"""
Some shortcuts for udi interface components

- LOGGER: to create log entries
- Custom: to access the custom data class
- ISY:    to communicate directly with the ISY (not commonly used)
"""
LOGGER = udi_interface.LOGGER
LOG_HANDLER = udi_interface.LOG_HANDLER
Custom = udi_interface.Custom
ISY = udi_interface.ISY


"""
framework url's
"""
URL_HOME = 'http://{g}/home'

class Controller(udi_interface.Node):
    id = 'hdctrl'

    def __init__(self, polyglot, primary, address, name):
        """
        super
        self definitions
        data storage classes
        subscribes
        ready
        we exist!
        """
        super(Controller, self).__init__(polyglot, primary, address, name)

        # useful global variables
        self.poly = polyglot
        self.primary = primary
        self.address = address
        self.name = name

        # here are specific variables to this controller
        self.variable = None

        # Create data storage classes to hold specific data that we need
        # to interact with.  
        self.Parameters = Custom(polyglot, 'customparams')
        self.Notices = Custom(polyglot, 'notices')
        self.TypedParameters = Custom(polyglot, 'customtypedparams')
        self.TypedData = Custom(polyglot, 'customtypeddata')

        # Subscribe to various events from the Interface class.
        #
        # The START event is unique in that you can subscribe to 
        # the start event for each node you define.

        self.poly.subscribe(self.poly.START, self.start, address)
        self.poly.subscribe(self.poly.LOGLEVEL, self.handleLevelChange)
        self.poly.subscribe(self.poly.CUSTOMPARAMS, self.parameterHandler)
        self.poly.subscribe(self.poly.CUSTOMTYPEDPARAMS, self.typedParameterHandler)
        self.poly.subscribe(self.poly.CUSTOMTYPEDDATA, self.typedDataHandler)
        self.poly.subscribe(self.poly.POLL, self.poll)
        self.poly.subscribe(self.poly.STOP, self.stop)

        # Tell the interface we have subscribed to all the events we need.
        # Once we call ready(), the interface will start publishing data.
        self.poly.ready()

        # Tell the interface we exist.  
        self.poly.addNode(self)

    def start(self):
        self.Notices['hello'] = 'Start-up'

        self.last = 0.0
        # Send the profile files to the ISY if neccessary. The profile version
        # number will be checked and compared. If it has changed since the last
        # start, the new files will be sent.
        self.poly.updateProfile()

        # Send the default custom parameters documentation file to Polyglot
        # for display in the dashboard.
        self.poly.setCustomParamsDoc()

        # Initializing a heartbeat is an example of something you'd want
        # to do during start.  Note that it is not required to have a
        # heartbeat in your node server
        self.heartbeat(True)

        # Device discovery. Here you may query for your device(s) and 
        # their capabilities.  Also where you can create nodes that
        # represent the found device(s)
        if self.checkParams():
            self.discover() # only do discovery if gateway change
            # TODO this assumption may be wrong ; may need to do every start-up see Michel email
            # TODO pull best practice from HD node

    """
    Called via the CUSTOMPARAMS event. When the user enters or
    updates Custom Parameters via the dashboard. The full list of
    parameters will be sent to your node server via this event.

    Here we're loading them into our local storage so that we may
    use them as needed.

    New or changed parameters are marked so that you may trigger
    other actions when the user changes or adds a parameter.

    NOTE: Be carefull to not change parameters here. Changing
    parameters will result in a new event, causing an infinite loop.
    """
    def parameterHandler(self, params):
        self.Parameters.load(params)
        LOGGER.debug('Loading parameters now')
        if self.checkParams():
            self.discover() # only do discovery if gateway change

    """
    Called via the CUSTOMTYPEDPARAMS event. This event is sent When
    the Custom Typed Parameters are created.  See the checkParams()
    below.  Generally, this event can be ignored.

    Here we're re-load the parameters into our local storage.
    The local storage should be considered read-only while processing
    them here as changing them will cause the event to be sent again,
    creating an infinite loop.
    """
    def typedParameterHandler(self, params):
        self.TypedParameters.load(params)
        LOGGER.debug('Loading typed parameters now')
        LOGGER.debug(params)

    """
    Called via the CUSTOMTYPEDDATA event. This event is sent when
    the user enters or updates Custom Typed Parameters via the dashboard.
    'params' will be the full list of parameters entered by the user.

    Here we're loading them into our local storage so that we may
    use them as needed.  The local storage should be considered 
    read-only while processing them here as changing them will
    cause the event to be sent again, creating an infinite loop.
    """
    def typedDataHandler(self, params):
        self.TypedData.load(params)
        LOGGER.debug('Loading typed data now')
        LOGGER.debug(params)

    """
    Called via the LOGLEVEL event.
    """
    def handleLevelChange(self, level):
        LOGGER.info('New log level: {}'.format(level))

    """
    Called via the POLL event.  The POLL event is triggerd at
    the intervals specified in the node server configuration. There
    are two separate poll events, a long poll and a short poll. Which
    one is indicated by the flag.  flag will hold the poll type either
    'longPoll' or 'shortPoll'.

    Use this if you want your node server to do something at fixed
    intervals.
    """
    def poll(self, flag):
        if 'longPoll' in flag:
            LOGGER.debug('longPoll re-parse updateallfromserver (controller)')
        else:
            LOGGER.debug('shortPoll check for events (controller)')

    def query(self, command = None):
        """
        The query method will be called when the ISY attempts to query the
        status of the node directly.  You can do one of two things here.
        You can send the values currently held by Polyglot back to the
        ISY by calling reportDriver() or you can actually query the 
        device represented by the node and report back the current 
        status.
        """
        nodes = self.poly.getNodes()
        for node in nodes:
            nodes[node].reportDrivers()

    def updateProfile(self,command):
        LOGGER.info('update profile')
        st = self.poly.updateProfile()
        return st

    def discover(self, command = None):
        """
        Do discovery here. Called from controller start method
        and from DISCOVER command received from ISY
        """
        pass
        # if self.updateAllFromServer():
        #     for shade in self.shades_array:
        #         self.poly.addNode(Shade(self.poly, \
        #                                 self.address, \
        #                                 'shade{}'.format(shade['shadeId']), \
        #                                 shade["name"], \
        #                                 shade['shadeId']))
        #     for scene in self.scenes_array:
        #         self.poly.addNode(Scene(self.poly, \
        #                                 self.address, \
        #                                 "scene{}".format(scene["_id"]), \
        #                                 scene["name"], \
        #                                 scene["_id"]))

    def delete(self):
        """
        This is called by Polyglot upon deletion of the NodeServer. If the
        process is co-resident and controlled by Polyglot, it will be
        terminiated within 5 seconds of receiving this message.
        """
        LOGGER.info('bye bye ... deleted.')

    def stop(self):
        """
        This is called by Polyglot when the node server is stopped.  You have
        the opportunity here to cleanly disconnect from your device or do
        other shutdown type tasks.
        """
        LOGGER.info('NodeServer stopped.')

    def heartbeat(self,init=False):
        """
        This is a heartbeat function.  It uses the
        long poll interval to alternately send a ON and OFF command back to
        the ISY.  Programs on the ISY can then monitor this and take action
        when the heartbeat fails to update.
        """
        LOGGER.debug('heartbeat: init={}'.format(init))
        if init is not False:
            self.hb = init
        LOGGER.debug('heartbeat: hb={}'.format(self.hb))
        if self.hb == 0:
            self.reportCmd("DON",2)
            self.hb = 1
        else:
            self.reportCmd("DOF",2)
            self.hb = 0

    def checkParams(self):
        """
        This is using custom Params for gateway IP
        """
        gatewaycheck = self.gateway
        self.gateway = self.Parameters.gatewayip
        # if self.gateway is None:
        #     self.gateway = URL_DEFAULT_GATEWAY
        #     LOGGER.warn('checkParams: gateway not defined in customParams, using {}'.format(URL_DEFAULT_GATEWAY))
        #     self.Notices['gateway'] = 'Please note using default gateway address'
        # else:
        #     self.Notices.delete('gateway')
        #     try:
        #         socket.inet_aton(self.gateway)
        #         LOGGER.info("good ip")
        #     except socket.error:
        #         try:
        #             if type(eval(self.gateway)) == list:
        #                 self.gateway_array = eval(self.gateway)
        #                 self.gateway = self.gateway_array[0]
        #                 LOGGER.info('we have a list %s', self.gateway_array)
        #                 LOGGER.info("self.gateway = %s", self.gateway)
        #             else:
        #                 LOGGER.error('we have a bad gateway %s', self.gateway)
        #                 self.Notices['gateway'] = 'Please note bad gateway address check customParams'
        #         except:
        #             LOGGER.error('we also have a bad gateway %s', self.gateway)
        #             self.Notices['gateway'] = 'Please note bad gateway address check customParams'
        # if gatewaycheck != self.gateway:
        #     return True # gateway changed
        # else:
        #     return False # no gateway change
                    
    def removeNoticesAll(self, command = None):
        LOGGER.info('remove_notices_all: notices={}'.format(self.Notices))
        # Remove all existing notices
        self.Notices.clear()


    # Commands that this node can handle.  Should match the
    # 'accepts' section of the nodedef file.
    commands = {
        'QUERY': query,
    }

    # Status that this node has. Should match the 'sts' section
    # of the nodedef file.
    drivers = [
        {'driver': 'ST', 'value': 1, 'uom': 2},
    ]

