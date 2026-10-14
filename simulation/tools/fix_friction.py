import os
import re
wsl_home = r'\\wsl.localhost\Ubuntu-22.04\home\emre'
path = os.path.join(wsl_home, 'ardupilot_gazebo', 'models', 'zephyr', 'model.sdf')
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# Change friction back to 0.1 so it can slide for takeoff without flipping
text = re.sub(r'<mu>1.0</mu>', '<mu>0.1</mu>', text)
text = re.sub(r'<mu2>1.0</mu2>', '<mu2>0.1</mu2>', text)

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Friction set to 0.1 for smooth sliding takeoff!")
