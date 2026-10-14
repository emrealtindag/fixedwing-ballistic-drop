file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\run_drone.sh'
script_content = """#!/bin/bash
IP=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')
# Unset DISPLAY so it bypasses xterm which is crashing due to font errors
DISPLAY="" sim_vehicle.py -v ArduCopter -f gazebo-iris --console --out $IP:14550 --out tcpin:0.0.0.0:5762 --mavproxy-args="--streamrate=10"
"""
with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(script_content)
