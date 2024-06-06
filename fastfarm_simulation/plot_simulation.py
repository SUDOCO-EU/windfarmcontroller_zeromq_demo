import glob
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
import os

from rosco.toolbox.ofTools.fast_io import output_processing

import openfast_toolbox.io as io 
import openfast_toolbox.io.vtk_file 


if __name__ == "__main__":
    # ROSCO toolbox modules 
    root_path = os.path.dirname(os.path.abspath(__file__))

    # Define openfast output filenames
    filenames = (
        glob.glob(os.path.join(root_path, "FAST.Farm_IEA22MW.out")) +
        list(np.sort(glob.glob(os.path.join(root_path, "FAST.Farm_IEA22MW.T*.RO.dbg2"))))
    )
    vtkFileNames = np.sort(glob.glob(os.path.join(root_path,"vtk_ff", "FAST.*.Low.Dis*.vtk")))
    vtkFileNames = vtkFileNames[0:-1]  # Leave out last entry

    print(f"Importing files: {filenames}")

    # Instantiate fast_IO and load the simulation output files
    fast_out = output_processing.output_processing()
    fastout = fast_out.load_fast_out(filenames)
    fastfarm_data = fastout[0]
    
    if len(filenames) > 1:
        turbine_data = fastout[1::]

        # Produce plots
        fig, ax = plt.subplots(nrows=4, figsize=(8, 12))
        for vii, varname in enumerate(["NacHeading", "VS_GenPwr", "RotSpeed", "HorWindV"]):
            for ii in range(len(turbine_data)):
                ax[vii].plot(turbine_data[ii]["Time"], turbine_data[ii][varname], label=f"Turbine {ii+1}")
            ax[vii].grid(True)
            ax[vii].set_ylabel(varname)
            ax[vii].legend()

        ax[-1].set_xlabel("Time (s)")

    # Plot horizontal flow slices
    out_path = os.path.join(root_path, "flow_visualization")
    os.makedirs(out_path, exist_ok=True)

    # Plot figure per frame
    for vii, vtkFileName in enumerate(vtkFileNames):
        # Check if file already exists
        fout = os.path.join(out_path, f"{vii:04d}.png")
        if os.path.exists(fout):
            continue

        # Read header information
        with open(vtkFileName) as f:    
            content = f.readlines()
            time = float(content[1].split("time = ")[1].split(" seconds")[0])

        # Read Plane
        print(f"Reading file {vtkFileName}")
        vtk = io.vtk_file.VTKFile(vtkFileName)
        # print(vtk)  # Print useful information

        # Extract field into individual components
        u = vtk.point_data_grid['Velocity'][:,:,:,0]
        v = vtk.point_data_grid['Velocity'][:,:,:,1]
        w = vtk.point_data_grid['Velocity'][:,:,:,2]

        # Plot a cross section
        fig, ax = plt.subplots(nrows=3, figsize=(14, 9))
        
        levels = np.arange(2.0, 9.501, 0.05)
        im = ax[0].contourf(vtk.xp_grid, vtk.yp_grid, u[:, :, 0].T, levels=levels)
        fig.colorbar(im)
        ax[0].set_xlabel('x [m]')
        ax[0].set_ylabel('y [m]')
        ax[0].set_title(f'Streamwise velocity in horizontal plane at z = {vtk.zp_grid[0]} m; t = {time:.2f} s')
        ax[0].set_aspect('equal', adjustable='box')
        ax[0].set_xlim([np.min(vtk.xp_grid), np.max(vtk.xp_grid)])
        ax[0].set_ylim([np.min(vtk.yp_grid), np.max(vtk.yp_grid)])

        ids = np.where(turbine_data[0]["Time"] <= time)[0]
        for i, t in enumerate(turbine_data):
            if i == 0:
                color = "tab:blue"
                ls = "-"
            elif i == 1:
                color = "tab:orange"
                ls = "--"
            elif i == 2:
                color = "tab:green"
                ls = "-."
            ax[1].plot(t["Time"][ids], t["VS_GenPwr"][ids], linestyle=ls, color=color, label=f"T{i+1}")
            ax[1].plot(t["Time"][ids][-1], t["VS_GenPwr"][ids][-1], "o", color=color, label=None)
        ax[1].grid(True)
        ax[1].set_ylabel("Power (W)")
        ax[1].legend()
        ax[1].set_xlim([0.0, 900.0])
        ax[1].set_ylim([0.0, 12.0e6])

        for i, t in enumerate(turbine_data):
            if i == 0:
                color = "tab:blue"
                ls = "-"
            elif i == 1:
                color = "tab:orange"
                ls = "--"
            elif i == 2:
                color = "tab:green"
                ls = "-."
            ax[2].plot(t["Time"][ids], t["NacHeading"][ids], color=color, linestyle=ls, label=f"T{i+1}")
            ax[2].plot(t["Time"][ids][-1], t["NacHeading"][ids][-1], "o", color=color, label=None)
        ax[2].grid(True)
        ax[2].set_ylabel("Nacelle heading (deg)")
        ax[2].legend()
        ax[2].set_xlim([0, 900.0])
        ax[2].set_ylim([-30.0, 30.0])
        ax[2].set_xlabel("Time (s)")

        # Save figure as file
        # plt.show()
        plt.tight_layout()
        plt.savefig(fout, dpi=200)
        print(f"Horizontal flowfield slice saved to {fout}.")
        plt.close()

    plt.show()
