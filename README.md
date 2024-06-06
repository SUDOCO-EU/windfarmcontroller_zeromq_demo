# Demonstration of the ZeroMQ-based wind farm controller in ROSCO

The open-source [ROSCO](https://github.com/NREL/ROSCO) wind turbine controller includes a ZeroMQ communication interface that can send measurements and receive turbine control setpoints from an external source, e.g., a live-running Python or MATLAB script. This functionality is well suited for the implementation of a wind farm controller. This repository demonstrates how a Python-written wind farm controller can be tested in a FAST.Farm simulation in which the turbines are controlled using ROSCO for their turbine controllers.

This repository is heavily based on a set of simulation files from Maarten van den Broek (Sowento).


## Installation

We install the required dependencies in a dedicated Conda environment for ROSCO applications. Please ensure you have a recent and working installation of Conda. 

First, we install [ROSCO](https://github.com/nrel/ROSCO). You can follow the steps [here](https://rosco.readthedocs.io/en/latest/source/install.html), which in brief entail:

```
conda config --add channels conda-forge
conda create -y --name rosco-env python=3.10
conda activate rosco-env
```

and then we clone and checkout version v2.9.0 of ROSCO from the GitHub repository.

```
git clone https://github.com/NREL/ROSCO
cd ROSCO
git checkout v2.9.0
cd ..
```

We then compile the ROSCO controller with ZeroMQ.

```
conda install wisdem pyzmq pkg-config openfast compilers
cd rosco/controller
mkdir build
cd build
cmake ..
make install
```

You should see something along the lines of...

```
Scanning dependencies of target zmq_client
[  6%] Building C object CMakeFiles/zmq_client.dir/src/zmq_client.c.o
/home/bartdoekemeijer/openfast_scripts/ROSCO/rosco/controller/src/zmq_client.c: In function 'delete_blank_spaces_in_string':
/home/bartdoekemeijer/openfast_scripts/ROSCO/rosco/controller/src/zmq_client.c:14:16: warning: comparison between pointer and integer
   14 |         if(s[i]==" "|| s[i]=="\t")
      |                ^~
/home/bartdoekemeijer/openfast_scripts/ROSCO/rosco/controller/src/zmq_client.c:14:28: warning: comparison between pointer and integer
   14 |         if(s[i]==" "|| s[i]=="\t")
      |                            ^~
[  6%] Built target zmq_client
Scanning dependencies of target discon
[ 13%] Building Fortran object CMakeFiles/discon.dir/src/Constants.f90.o
[ 20%] Building Fortran object CMakeFiles/discon.dir/src/ROSCO_Types.f90.o
[ 26%] Building Fortran object CMakeFiles/discon.dir/src/Filters.f90.o
[ 33%] Building Fortran object CMakeFiles/discon.dir/src/Functions.f90.o
[ 40%] Building Fortran object CMakeFiles/discon.dir/src/ControllerBlocks.f90.o
[ 46%] Building Fortran object CMakeFiles/discon.dir/src/Controllers.f90.o
[ 53%] Building Fortran object CMakeFiles/discon.dir/src/SysFiles/SysGnuLinux.f90.o
[ 60%] Building Fortran object CMakeFiles/discon.dir/src/ExtControl.f90.o
[ 66%] Building Fortran object CMakeFiles/discon.dir/src/ROSCO_Helpers.f90.o
[ 73%] Building Fortran object CMakeFiles/discon.dir/src/ReadSetParameters.f90.o
[ 80%] Building Fortran object CMakeFiles/discon.dir/src/ROSCO_IO.f90.o
[ 86%] Building Fortran object CMakeFiles/discon.dir/src/ZeroMQInterface.f90.o
[ 93%] Building Fortran object CMakeFiles/discon.dir/src/DISCON.F90.o
[100%] Linking Fortran shared library libdiscon.so
[100%] Built target discon
Install the project...
-- Install configuration: "RelWithDebInfo"
-- Installing: /home/bartdoekemeijer/openfast_scripts/ROSCO/rosco/controller/../../lib/libdiscon.so
```

To finish installing ROSCO, pip install the package,

```
cd ../../..
pip install -e .
cd ..
```

Then, download and install the [OpenFAST Toolbox](https://github.com/OpenFAST/openfast_toolbox) manually, by

```
git clone http://github.com/OpenFAST/openfast_toolbox
cd openfast_toolbox
git checkout 353643e
pip install -e .
cd ..
```

Then, clone and install the repository at hand, as

```
git clone https://github.com/Bartdoekemeijer/windfarmcontroller_zeromq_demo
cd windfarmcontroller_zeromq_demo
pip install -e .
cd ..
```


## Quick Start

In principle, the entire simulation is set up to run out of the box. The only thing you must link is that you copy the ROSCO-compiled library (libdiscon.so) to the turbine controller files.

```
cp /path/to/rosco/repository/rosco/lib/libdiscon.so ./windfarmcontroller_zeromq_demo/fastfarm_simulation/wind_turbines/turbine_controllers/libdiscon.T1.so
cp /path/to/rosco/repository/rosco/lib/libdiscon.so ./windfarmcontroller_zeromq_demo/fastfarm_simulation/wind_turbines/turbine_controllers/libdiscon.T2.so
cp /path/to/rosco/repository/rosco/lib/libdiscon.so ./windfarmcontroller_zeromq_demo/fastfarm_simulation/wind_turbines/turbine_controllers/libdiscon.T3.so
```

Finally, to run the actual simulation, we must start the FAST.Farm simulation and the Python wind farm controller in parallel. We do that using the `&` operator in the Linux terminal.

```
cd fastfarm_simulation
(FAST.Farm FAST.Farm_IEA22MW.fstf) & (python "../wind_farm_controller/wake_steering_controller.py")
```

The simulation will run and may take about an hour to complete. You can run the `plot_simulation.py` to plot the progress of the simulation and to convert the .vtk flow field slices into `.png` snapshots. You can also use `generate_flowfield_video.sh` to both produce the video frames and then stitch the frames together using `ffmpeg`.

The wind farm controller logs its output to the file `wind_farm_controller/wind_farm_controller.log`.


# License

BSD 3-Clause License

Copyright (c) 2024, Shell Global Solutions International B.V., All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted
provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this list of conditions
and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice, this list of
conditions and the following disclaimer in the documentation and/or other materials provided
with the distribution.

* Neither the name of the copyright holder nor the names of its contributors may be used to
endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR
IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER
OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.