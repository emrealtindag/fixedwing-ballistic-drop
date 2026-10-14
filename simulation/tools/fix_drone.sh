#!/bin/bash
export PATH=$PATH:$HOME/.local/bin:$HOME/ardupilot/Tools/autotest
killall -9 arducopter mavproxy.py sim_vehicle.py arduplane 2>/dev/null

DISPLAY="" sim_vehicle.py -v ArduPlane -w -f JSON --console --out tcpin:0.0.0.0:5777 --out tcpin:0.0.0.0:5778 --mavproxy-args="--streamrate=10 --out udpin:0.0.0.0:14550"
