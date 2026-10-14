file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\run_drone.sh'
script_content = """#!/bin/bash
sim_vehicle.py -v ArduCopter -f gazebo-iris --console --out tcpin:0.0.0.0:5762 --mavproxy-args="--streamrate=10"
"""
with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(script_content)
