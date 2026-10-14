import re
filepath = r'\\wsl.localhost\Ubuntu-22.04\home\emre\run_drone.sh'
with open(filepath, 'r') as f:
    content = f.read()

# Replace IP extraction with hardcoded IP or just replace $IP
content = content.replace('IP=$(cat /etc/resolv.conf | grep nameserver | awk \'{print $2}\')', 'IP="172.31.176.1"')

# Add another TCP out port (5778) for Mission Planner
if '5778' not in content:
    content = content.replace('--out tcpin:0.0.0.0:5777', '--out tcpin:0.0.0.0:5777 --out tcpin:0.0.0.0:5778')

with open(filepath, 'w', newline='\n') as f:
    f.write(content)
