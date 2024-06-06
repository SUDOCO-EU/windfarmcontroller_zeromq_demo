import numpy as np
import matplotlib.pyplot as plt
import os
import yaml

from floris.tools import FlorisInterface
from flasc.visualization import plot_floris_layout, plot_layout_with_waking_directions


"""
This function adds the turbine specifications (rotor diameter, hub height, Cp and Ct curves) to an
input FLORIS .yaml file and then exports it. This is part of the workflow in which a standard
FLORIS input file with NREL 5MW turbines is converted into a FLORIS input file that matches the
turbine locations and specifications for the simulation at hand.
"""


# TURBINE CONSTANTS
AIR_DENSITY = 1.225
ROTOR_DIAMETER = 284.0
HUB_HEIGHT = 170.0


def load_steady_state_tables(plot=False):
    """Load the steady-state turbine performance curves from the 'iea-22-280-rwt-steady-states-of.yaml'
    file that can be found in the IEA-22MW GitHub repository.

    Args:
        plot (bool, optional): Plot the turbine performance curves. Defaults to False.
    """

    # Load the steady-state table file
    root_path = os.path.dirname(os.path.abspath(__file__))
    fn = os.path.join(
        root_path, "..", "fastfarm_simulation", "wind_turbines", "IEA-22-280-RWT",
        "outputs", "01_steady_states", "OpenFAST", "iea-22-280-rwt-steady-states-of.yaml"
    )

    with open(fn) as stream:
        ss_data = yaml.safe_load(stream)

    # Reshape the results into a list of floats
    wind_speed = []
    power = []
    thrust = []
    for c in ss_data["cases"]:
        wind_speed.append(c["configuration"]["wind_speed"])
        power.append(c["outputs"]["integrated"]["mechanical_power"])
        thrust.append(c["outputs"]["integrated"]["rotor_thrust"])

    # Calculate the power and thrust coefficients based on absolute values
    rotor_swept_area = 0.25 * np.pi * ROTOR_DIAMETER**2.0
    cp = [p / (0.5 * AIR_DENSITY * w**3.0 * rotor_swept_area) for p, w in zip(power, wind_speed)]
    ct = [t / (0.5 * AIR_DENSITY * w**2.0 * rotor_swept_area) for t, w in zip(thrust, wind_speed)]

    # Finally, plot the results
    if plot:
        fig, ax = plt.subplots(nrows=2, sharex=True)
        ax[0].plot(wind_speed, power)
        ax[0].grid(True)
        ax[0].set_ylabel("Power (W)")
        ax[1].plot(wind_speed, thrust)
        ax[1].grid(True)
        ax[1].set_ylabel("Thrust (N)")
        ax[1].set_xlabel("Wind speed (m/s)")

        fig, ax = plt.subplots(nrows=2, sharex=True)
        ax[0].plot(wind_speed, cp)
        ax[0].grid(True)
        ax[0].set_ylabel("Power coefficient (-)")
        ax[1].plot(wind_speed, ct)
        ax[1].grid(True)
        ax[1].set_ylabel("Thrust coefficient (-)")
        ax[1].set_xlabel("Wind speed (m/s)")

    # Wrap into a dict and return
    power_thrust_table = {"power": cp, "thrust": ct, "wind_speed": wind_speed}

    return power_thrust_table


if __name__ == "__main__":
    # Load a base FLORIS file in which the turbine locations are already correct
    root_path = os.path.dirname(os.path.abspath(__file__))
    fn = os.path.join(root_path, "three_turbine_case.yaml")
    fi = FlorisInterface(fn)

    # Load the steady-state tables from an external file
    power_thrust_table = load_steady_state_tables(plot=True)

    # Update FLORIS turbine definitions to the IEA 22MW wind turbines
    fi.calculate_wake()
    turbine_type = dict({
        "turbine_type": "iea_22mw",
        "generator_efficiency": 1.0,
        "hub_height": HUB_HEIGHT,
        "pP": 1.88,
        "pT": 1.88,
        "rotor_diameter": ROTOR_DIAMETER,
        "TSR": 9.153,
        "ref_density_cp_ct": AIR_DENSITY,
        "ref_tilt_cp_ct": 6.0,
        "power_thrust_table": power_thrust_table,
    })
    fi.reinitialize(turbine_type=3*[turbine_type])

    # Calculate turbine powers to verify implementation
    fi.calculate_wake()
    turbine_powers = fi.get_turbine_powers()

    # Export FLORIS as a dictionary
    fi_dict = fi.floris.as_dict()
    fi_dict["farm"]["turbine_library_path"] = ""
    fn = os.path.join(root_path, "three_turbine_case.yaml")
    with open(fn, 'w') as stream:
        yaml.safe_dump(fi_dict, stream)

    # Plot layout
    plot_floris_layout(fi=fi, plot_terrain=False)
    plot_layout_with_waking_directions(fi=fi)

    plt.show()
