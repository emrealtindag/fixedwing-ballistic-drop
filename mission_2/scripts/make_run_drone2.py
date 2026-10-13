file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\run_drone.sh'
script_content = """#!/bin/bash
# Force MAVProxy to host a TCP server on port 5762 that Windows can easily connect to
sim_vehicle.py -v ArduCopter -f gazebo-iris --console --out tcpin:0.0.0.0:5762
"""
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(script_content)
