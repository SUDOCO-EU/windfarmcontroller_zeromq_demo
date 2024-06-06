import os
import numpy as np
from wfc_zmq_server import wfc_zmq_server

from floris.tools import FlorisInterface
from floris.tools.optimization.yaw_optimization.yaw_optimizer_sr import YawOptimizationSR


"""In this script, we define the wind farm controller class that receives measurements from
the turbine controllers and sends setpoints back. The 'class' formulation allows it to
save variables to self and thus have a 'memory'.

When this file is run as a script, it will launch the wind farm controller instance that
actively communicates with the ROSCO instances. It will remain running while the FAST.Farm
simulation continues to run.
"""


class wfc_controller():
    """The wind farm controller class. This class should, as a minimum, have the functions
    __init__() and update(). The update() function is called for each turbine and for each
    timestep to communicate measurements and control setpoints. This class is where you can
    build your wind farm control logic in.
    """

    def __init__(self, n_turbines: int, update_rate: float = 10.0, memory_size: int = 60):
        """Initialize the wind farm controller class.

        Args:
            n_turbines (int): Number of turbines in the simulation.
            update_rate (float, optional): Time rate at which wind farm control setpoints
              should be recalculated. Defaults to 10.0.
            memory_size (int, optional): Memory size for the measurements, i.e., the last [X]
              measurements are saved internally. Defaults to 60. For ZeroMQ communication frequency
              of 2.0 seconds, this means that the last 120 seconds of measurements is saved to
              the wfc_controller class.
        """

        # Initialize a list for turbine measurements, by default last 1000 entries
        self.measurements_history = [[dict() for _ in range(memory_size)] for _ in range(n_turbines)]

        # Initialize wind farm control optimal setpoints as zeros
        self.opt_yaw_angles = np.zeros(n_turbines, dtype=float)  # Assume zero misalignment at the start
        self.opt_pitch_angles = np.zeros(n_turbines, dtype=float)  # Assume zero pitch offsets at the start

        # Initialize a counter so we only update the wfc setpoints every [x] seconds, by default 10 s
        self.t_last_update = -99999  # Time of last controller update
        self.t_update_rate = update_rate  # Time between wind farm control setpoint updates

        # Load FLORIS object for the wind farm at hand
        root_path = os.path.dirname(os.path.abspath(__file__))
        self.fi = FlorisInterface(os.path.join(root_path, "three_turbine_case.yaml"))

    def update_measurement_history(self, id, measurements):
        """Add a turbine's measurements to the memory.

        Args:
            id (int): Turbine number, assuming '1' is the first turbine, '2' is the second, and so on
            measurements (dict): Dictionary with turbine measurements for this timestamp
        """
        ti = int(id - 1)
        self.measurements_history[ti][:-1] = self.measurements_history[ti][1:]
        self.measurements_history[ti][-1] = measurements

    def optimize_yaw_angles(self, id, current_time):
        """User-defined function that optimizes the turbine yaw angles using FLORIS at regular
        intervals. It won't apply any wake steering until 1 minute has passed in the simulation,
        and will only update the setpoints at set intervals.

        Args:
            id (int): Turbine number, assuming '1' is the first turbine, '2' is the second, and so on
            current_time (float): Current time in the simulation in seconds
        """

        # Skip wake steering for the first 60 seconds of the simulation
        if (current_time < 60.0):
            return None

        # Only update the wind-farm-wide wake steering controller setpoints if we are communicating with the first turbine.
        # Namely, this function is called for every turbine individually, so for one particular timestep this function is
        # called 3 times, e.g., if you have 3 turbines. We only need to update the setpoints once, so we choose that to happen
        # when we communicate with turbine 1.
        if not (id == 1):
            return None

        # Only update the wind-farm-wide wake steering controller setpoints at set intervals
        if not (current_time >= (self.t_last_update + self.t_update_rate)):
            print(f"[t={current_time:.1f} s] Using zero-order hold for wind farm controller setpoints.")
            return None

        # If we pass all those checks, we can proceed to update the farm controller setpoints
        print("Updating the wind farm controller setpoints...")
        self.t_last_update = current_time  # Update time of last update to reset the counter

        # Now estimate the freestream wind condition based on the first turbine and the average of the last 10 measurements
        freestream_windspeed = np.mean([d["HorWindV"] for d in self.measurements_history[0][-10:]])
        print(f"Estimated freestream wind speed based on last 10 measurements of most upstream turbine: {freestream_windspeed}")

        # Perform the wake steering optimization in FLORIS
        fi = self.fi  # Load FLORIS from self
        fi.reinitialize(wind_directions=[270.0], wind_speeds=[freestream_windspeed])  # Update ambient conditions
        yaw_opt = YawOptimizationSR(
            fi=fi,
            minimum_yaw_angle=-25.0,
            maximum_yaw_angle=25.0,
            exploit_layout_symmetry=False
        )
        df_opt = yaw_opt.optimize()  # Perform the yaw optimization

        # Update the optimal yaw angle offsets
        self.opt_yaw_angles = df_opt.loc[0, "yaw_angles_opt"]
        print(f"[WFC]: Optimal yaw angles updated to {self.opt_yaw_angles} based on FLORIS optimization.")

    def optimize_pitch_angles(self):
        """User-defined function that optimizes the turbine blade pitch angles. For this application,
        the blade pitch angles are kept constant at zero."""
        return None

    def update(self, id: int, current_time: float, measurements: dict):
        """
        Users need to define this function to implement wind farm controller.
        The user defined function should take as argument the turbine id, the
        current time and current measurements and return the setpoints
        for the particular turbine for the current time. It should ouput the
        setpoints as a dictionary whose keys should be as defined in
        wfc_zmq_server.wfc_interface.


        Args:
            id (int): Turbine number, assuming '1' is the first turbine, '2' is the second, and so on
            current_time (float): Current time in the simulation in seconds
            measurements (dict): Dictionary of the turbine measurements passed from ROSCO
              to this wind farm controller interface.

        Returns:
            setpoints (dict): Dictionary with the wind farm control setpoints for turbine 'id'
        """

        # Save the measurements internally to memory
        self.update_measurement_history(id, measurements)

        # Re-calculate the wind farm controller setpoints
        self.optimize_yaw_angles(id=id, current_time=current_time)  # Optimizes yaw angles for wake steering at set intervals
        self.optimize_pitch_angles()  # Does nothing right now

        # Gather the setpoints and send to ROSCO
        setpoints = dict({
            "ZMQ_YawOffset": self.opt_yaw_angles[id-1],
            "ZMQ_PitOffset(1)": self.opt_pitch_angles[id-1],
            "ZMQ_PitOffset(2)": self.opt_pitch_angles[id-1],
            "ZMQ_PitOffset(3)": self.opt_pitch_angles[id-1]
        })
        return setpoints


if __name__ == "__main__":
    """Start the ZeroMQ server for wind farm control"""

    # Start the server at the following address
    root_path = os.path.dirname(os.path.abspath(__file__))
    logfile = os.path.join(root_path, "wind_farm_controller.log")
    network_address = "tcp://*:5555"
    server = wfc_zmq_server(network_address, timeout=60.0, verbose=True, logfile=logfile)

    # Provide the wind farm control algorithm as the wfc_controller method of the server
    server.wfc_controller = wfc_controller(n_turbines=3, update_rate=10.0, memory_size=60)

    # Run the server to continuously receive measurements and send setpoints
    server.runserver()


# if __name__ == "__main__":
#     """Test the wind farm controller by hand"""
#     w = wfc_controller(n_turbines=3, update_rate=10.0)
#     for current_time in np.arange(0.0, 300.0, 1.0):
#         for id in [1, 2, 3]:
#             measurements = {'ZMQ_ID': float(id), 'iStatus': 1.0, 'Time': float(current_time), 'VS_MechGenPwr': 9446699.0, 'HorWindV': 8.412}
#             w.update(id=id, current_time=current_time, measurements=measurements)
