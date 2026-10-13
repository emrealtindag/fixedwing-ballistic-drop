#!/bin/bash
export PATH=$PATH:$HOME/ardupilot/Tools/autotest
sim_vehicle.py -v ArduPlane -f gazebo-zephyr --console
