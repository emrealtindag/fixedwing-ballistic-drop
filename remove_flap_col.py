import os
import re
wsl_home = r'\\wsl.localhost\Ubuntu-22.04\home\emre'
path = os.path.join(wsl_home, 'ardupilot_gazebo', 'models', 'zephyr', 'model.sdf')
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# REMOVE Flap Collisions so they physically cannot hit the ground and launch the plane
text = re.sub(r'<collision name="collision">\s*<pose>.*?0.32445671</pose>\s*<geometry>\s*<box>.*?</box>\s*</geometry>\s*</collision>', '', text, flags=re.DOTALL)
text = re.sub(r'<collision name="collision">\s*<pose>.*?-0.32445671</pose>\s*<geometry>\s*<box>.*?</box>\s*</geometry>\s*</collision>', '', text, flags=re.DOTALL)

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Removed Flap Collisions!")
