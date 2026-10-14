#!/bin/bash
export PATH=$PATH:$HOME/ardupilot/Tools/autotest
sim_vehicle.py -v ArduPlane -f JSON -w --console
