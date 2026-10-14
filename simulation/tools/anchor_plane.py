import os
import re
wsl_home = r'\\wsl.localhost\Ubuntu-22.04\home\emre'
path = os.path.join(wsl_home, 'ardupilot_gazebo', 'models', 'zephyr', 'model.sdf')
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# Change friction from 0.05 to 1.0 to completely anchor the plane until armed
text = re.sub(r'<mu>0.05</mu>', '<mu>1.0</mu>', text)
text = re.sub(r'<mu2>0.5</mu2>', '<mu2>1.0</mu2>', text)

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Friction anchored to 1.0!")
