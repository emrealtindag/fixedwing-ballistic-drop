import re
with open('/home/emre/ardupilot_gazebo/models/techpod_with_ardupilot/techpod.sdf', 'r') as f:
    sdf = f.read()

for match in re.finditer(r'<plugin name="elevator".*?</plugin>', sdf, re.DOTALL):
    print(match.group(0))
