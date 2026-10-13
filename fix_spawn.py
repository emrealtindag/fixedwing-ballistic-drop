import os
import re
wsl_home = r'\\wsl.localhost\Ubuntu-22.04\home\emre'
path = os.path.join(wsl_home, 'ardupilot_gazebo', 'worlds', 'teknofest_world.world')
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# Change the spawn pose from 0.1 to 0.5 meters high so it drops safely instead of exploding out of the ground
text = re.sub(r'<pose>0 0 0.1 0 0 0</pose>', '<pose>0 0 0.5 0 0 0</pose>', text)

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Spawn height adjusted!")
