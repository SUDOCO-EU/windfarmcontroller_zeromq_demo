import os
import numpy as np
from wfc_zmq_server import wfc_zmq_server

from floris.tools import FlorisInterface
from floris.tools.optimization.yaw_optimization.yaw_optimizer_sr import YawOptimizationSR


class wfc_controller():
    def __init__(self, n_turbines: int, update_rate: float = 10.0, memory_size: int = 60):
        """Initialize a memory"""
        # Initialize a list for turbine measurements, by default last 1000 entries
        self.measurements_history = [[dict() for _ in range(memory_size)] for _ in range(n_turbines)]

        # Initialize optimal conditions as zeros
        self.opt_yaw_angles = np.zeros(n_turbines, dtype=float)  # Assume zero misalignment at the start
        self.opt_pitch_angles = np.zeros(n_turbines, dtype=float)  # Assume zero pitch offsets at the start

        # Initialize a counter so we only update the wfc setpoints every [x] seconds, by default 10 s
        self.t_last_update = -99999  # Time of last controller update
        self.t_update_rate = update_rate  # Time between wind farm control setpoint updates

        # Load FLORIS object
        root_path = os.path.dirname(os.path.abspath(__file__))
        self.fi = FlorisInterface(os.path.join(root_path, "three_turbine_case.yaml"))

    def update_measurement_history(self, id, measurements):
        ti = int(id - 1)
        self.measurements_history[ti][:-1] = self.measurements_history[ti][1:]
        self.measurements_history[ti][-1] = measurements

    def optimize_yaw_angles(self, id, current_time):
        # Skip the first 60 seconds of a simulation
        if (current_time < 60.0):
            return None

        # Only update the wind-farm-wide wake steering controller setpoints if we are communicating with the first turbine 1
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

        # Perform the wake steering optimization in FLORI
        fi = self.fi
        fi.reinitialize(wind_directions=[270.0], wind_speeds=[freestream_windspeed])
        yaw_opt = YawOptimizationSR(
            fi=fi,
            minimum_yaw_angle=-25.0,
            maximum_yaw_angle=25.0,
            exploit_layout_symmetry=False
        )
        df_opt = yaw_opt.optimize()
        self.opt_yaw_angles = df_opt.loc[0, "yaw_angles_opt"]
        print(f"[WFC]: Optimal yaw angles updated to {self.opt_yaw_angles} based on FLORIS optimization.")

    def optimize_pitch_angles(self):
        # We never update the turbine blade pitch angles
        return None

    def update(self, id: int, current_time: float, measurements: dict):
        """
        Users needs to define this function to implement wind farm controller.
        The user defined function should take as argument the turbine id, the
        current time and current measurements and return the setpoints
        for the particular turbine for the current time. It should ouput the
        setpoints as a dictionary whose keys should be as defined in
        wfc_zmq_server.wfc_interface. The wfc_controller method of the wfc_zmq_server
        should be overwriten with this fuction, otherwise, an exception is raised and
        the simulation stops.
        """

        # Update measurements internally to track
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


# if __name__ == "__main__":
#     """Test the wind farm controller by hand"""
#     w = wfc_controller(n_turbines=3, update_rate=10.0)
#     for current_time in np.arange(0.0, 300.0, 1.0):
#         for id in [1, 2, 3]:
#             measurements = {'ZMQ_ID': float(id), 'iStatus': 1.0, 'Time': float(current_time), 'VS_MechGenPwr': 9446699.0, 'HorWindV': 8.412}
#             w.update(id=id, current_time=current_time, measurements=measurements)


if __name__ == "__main__":
    """Start the ZeroMQ server for wind farm control"""

    # Start the server at the following address
    root_path = os.path.dirname(os.path.abspath(__file__))
    logfile = os.path.join(root_path, "wind_farm_controller.log")
    network_address = "tcp://*:5555"
    server = wfc_zmq_server(network_address, timeout=60.0, verbose=True, logfile=logfile)

    # Provide the wind farm control algorithm as the wfc_controller method of the server
    server.wfc_controller = wfc_controller(n_turbines=3, update_rate=10.0, memory_size=60)

    # Run the server to receive measurements and send setpoints
    server.runserver()
