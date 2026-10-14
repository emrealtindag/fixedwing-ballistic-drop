file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\run_drone.sh'
script_content = """#!/bin/bash
IP=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')
sim_vehicle.py -v ArduCopter -f gazebo-iris --console --out $IP:14551
"""
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(script_content)
import os
os.system(rf'wsl -e bash -c "chmod +x /home/emre/run_drone.sh"')
