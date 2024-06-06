# Copyright 2019 NREL

# Licensed under the Apache License, Version 2.0 (the "License"); you may not use
# this file except in compliance with the License. You may obtain a copy of the
# License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.


import numpy as np
import os
import zmq
import logging
from rosco.toolbox.ofTools.util.FileTools import load_yaml


logger = logging.getLogger(__name__)
# Choose logging level below
logger.setLevel(logging.INFO)       # For a basic level of logs 
# logger.setLevel(logging.DEBUG)    # For more detailed logs helpful for debugging


class wfc_zmq_server:
    """Server side implementation of wind farm control interface for the ROSCO using ZeroMQ

    This class enables users to receive measurements from ROSCO and then send back control
    setpoints (generator torque, nacelle heading and/or blade pitch angles) using ZeroMQ
    messaging library.

    Attirbutes
    ----------
    network_address : str
        Address of the server usually in the format "tcp://*:5555"
    timeout : float
        Time till server time out
    verbose : bool
        Prints details of messages being passed using the server
    logfile : string
        Path of the logfile; if logfile is not provided, logging is disabled

    methods
    -------
    runserver()
        Run the server to recieve and send data to ROSCO controllers
    wfc_controller(id, current_time)
        User defined method that contains the controller algorithm.
    """

    # Read the interface file to obtain the structure of measurements and setpoints
    interface_file = os.path.realpath(
        os.path.join(
            os.path.dirname(__file__), "wfc_interface.yaml"
        )
    )
    wfc_interface = load_yaml(interface_file)

    def __init__(self, network_address="tcp://*:5555", timeout=600.0, verbose=False,logfile=None):
        """Instanciate the server"""
        self.network_address = network_address
        self.timeout = timeout
        self.verbose = verbose
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.connections = wfc_zmq_connections(self.wfc_interface)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.bind(self.network_address)
        if self.verbose:
            print(
                f"Successfully established connection a ZeroMQ server at {network_address}"
            )
        
        if logfile is not None:
            print(logfile)
            logger_filehandler = logging.FileHandler(logfile, "w+")
            logger_filehandler.setFormatter(logging.Formatter("%(asctime)s: %(message)s"))
            logger.addHandler(logger_filehandler)
        else:
            logging.disable()
            if self.verbose:
                print('Logging disabled')

        logger.info(
            f"Successfully established connection a ZeroMQ server at {network_address}"
        )
        
        self.wfc_controller = None  # Instantiate empty wfc_controller


    def runserver(self):
        """Run the server to get measurements and send setpoints to ROSCO"""
        connect_zmq = True
        while connect_zmq:
            # Wait for and obtain measurements from ROSCO
            measurements = self._get_measurements()

            # Obtain the identifier from the measurments
            id = int(measurements["ZMQ_ID"])

            # Add turbie id to the list of connected turbines
            self.connections._add_unique(id)

            # Update the measurements of the turbine
            self.connections._update_measurements(id, measurements)
            try:
                # Try to get the setpoints of the turbine
                logger.debug(f"Trying to get setpoints for id = {id}")
                self._get_setpoints(id, measurements)
            except NotImplementedError as e:
                # Disconnect from the server and raise an error
                # if the user has not defined a wind farm controller
                self._disconnect()
                logger.critical(f'Disconnected due to wfc_controller not being defined by the user')
                raise e
            else:
                # If setpoints are successfully read then
                # send the setpoint to the ROSCO client
                self._send_setpoints(id)

                # Check if there are no clients connected to the server
                # and if so, disconnect the server
                logger.debug('Checking for disconnect')
                connect_zmq = self._check_for_disconnect()

    def _get_setpoints(self, id, measurements):
        """Get current setpoint from the wind farm controller

        Gets the setpoint for the current turbine at the current time step
        """
        current_time = self.connections.measurements[id]["Time"]
        logger.debug(
            f"Asking wfc_controller for setpoints at time = {current_time} for id = {id}"
        )
        setpoints = self.wfc_controller.update(id, current_time, measurements)
        logger.info(f"Received setpoints {setpoints} from wfc_controller for time = {current_time} and id = {id}")

        for s in self.wfc_interface["setpoints"]:
            self.connections.setpoints[id][s] = setpoints.get(s, 0)
            logger.debug(f'Set setpoint {s} in the connections list to {setpoints.get(s,0)} for id = {id}')

    # def wfc_controller(self, id, current_time, measurements):
    #     """User defined wind farm controller

    #     Users needs to overwrite this method by their wind farm controller.
    #     The user defined method should take as argument the turbine id, the
    #     current time and current measurements and return the setpoints
    #     for the particular turbine for the current time. It should ouput the
    #     setpoints as a dictionary whose keys should be as defined in
    #     wfc_zmq_server.wfc_interface. If user does not overwrite this method,
    #     an exception is raised and the simulation stops.

    #     Examples
    #     --------
    #     >>> # Define the wind farm controller
    #     >>> def wfc_controller(id, current_time):
    #     >>>     if current_time <= 10.0:
    #     >>>         YawOffset = 0.0
    #     >>>     else:
    #     >>>         if id == 1:
    #     >>>             YawOffset = -10.0
    #     >>>         else:
    #     >>>             YawOffset = 10
    #     >>>     setpoints = {}
    #     >>>     setpoints["ZMQ_YawOffset"] = YawOffset
    #     >>>     return setpoints
    #     >>>
    #     >>> # Overwrite the wfc_controller method of the server
    #     >>> server.wfc_controller = wfc_controller
    #     """
    #     logger.critical("User defined wind farm controller not found")
    #     raise NotImplementedError("Wind farm controller needs to be defined.")

    def _get_measurements(self):
        """Receive measurements from ROSCO .dll"""
        if self.verbose:
            print("[%s] Waiting to receive measurements from ROSCO...")

        # message_in = self.socket.recv_string()
        # Initialize a poller for timeouts
        poller = zmq.Poller()
        poller.register(self.socket, zmq.POLLIN)
        timeout_ms = int(self.timeout * 1000)
        # poller.poll(timeout_ms)
        events = poller.poll(timeout_ms)
        if self.socket in dict(events):
            # if poller.poll(timeout_ms):
            # Receive measurements over network protocol
            logger.debug(
                f"Checked for timeout and waiting for measurements from a ROSCO client"
            )
            message_in = self.socket.recv_string()
            print(f"Raw message: {message_in}")
            logger.debug(f"Received raw message: {message_in} ")
        else:
            # raise IOError("[%s] Connection to '%s' timed out."
            #   % (self.identifier, self.network_address))
            logger.info(f"Connection timed out")
            raise IOError("Connection timed out")

        # Convert to individual strings and then to floats
        meas_float = message_in
        meas_float = meas_float.replace("\x00", "").split(",")
        meas_float = [float(m) for m in meas_float]

        # Convert to a measurement dict
        meas_dict = {}
        for i_meas, meas in enumerate(self.wfc_interface["measurements"]):
            meas_dict[meas] = meas_float[i_meas]
        logger.info(f"Received message (formatted): {meas_dict}")
        if self.verbose:
            print("[%s] Measurements received:", meas_dict)

        return meas_dict

    def _send_setpoints(self, id):
        """Send setpoints to ROSCO .dll ffor individual turbine control"""

        # Create a string message with setpoints to send to ROSCO
        message_out = ", ".join(
            [f"{s:016.5f}" for s in self.connections.setpoints[id].values()]
        ).encode("utf-8")

        #  Send reply back to client
        
        logger.debug(f"Raw setpoints to be sent to id = {id} is {message_out}")
        if self.verbose:
            print("[%s] Sending setpoint string to ROSCO: %s." % (id, message_out))

        # Send control setpoints over network protocol
        self.socket.send(message_out)
        logger.info(f"Sent setpoints {self.connections.setpoints[id]} to id = {id}")

        if self.verbose:
            print("[%s] Setpoints sent successfully." % id)

    def _check_for_disconnect(self):
        """Disconnect if no clients are connected to the server"""
        num_connected = sum(self.connections.connected.values())
        logger.debug(f'Still connected to {num_connected} clients')
        if num_connected > 0:
            connect_zmq = True
            if self.verbose:
                print("Still connected to ", num_connected, " ROSCO clients")
        else:
            connect_zmq = False
            logger.info('Shutting down server as all the clients have dropped off')
            self._disconnect()
        return connect_zmq

    def _disconnect(self):
        """Disconnect from zmq server"""
        logger.info('Socket terminated')
        self.socket.close()
        context = zmq.Context()
        context.term()


class wfc_zmq_connections:
    """
    This class is used to track the current ROSCO client connections,
    their current measurements and setpoints.
    """

    # Dictionary of ROSCO clients connected to the server
    connected = {}

    def __init__(self, wfc_interface):
        self.wfc_interface = wfc_interface
        self.setpoints = {}
        self.measurements = {}

    def _add_unique(self, id):
        """Add to the dictionary of connected client

        Add the current turbine to the dictionary of connected clients,
        if it has not been added before. Next, initilize the measurements
        and setpoints for the turbine to 0.
        """
        if id not in wfc_zmq_connections.connected.keys():
            wfc_zmq_connections.connected.update({id: True})
            logger.info(f"Connected to a new ROSCO with id = {id}")

            self.setpoints.update(
                {id: {s: 0.0 for s in self.wfc_interface["setpoints"]}}
            )  # init setpoints with zeros
            self.measurements.update(
                {id: {s: 0.0 for s in self.wfc_interface["measurements"]}}
            )  # init measurements with zeros

    def _update_measurements(self, id, measurements):
        """Update the measurements and remove turbine from connected clients"""
        self.measurements.update({id: measurements})
        logger.debug(f"Updated measurements for ROSCO with id = {id} ")
        if measurements["iStatus"] == -1:
            wfc_zmq_connections.connected[id] = False
            logger.info(f"Received disconnect signal from ROSCO with id = {id}")
