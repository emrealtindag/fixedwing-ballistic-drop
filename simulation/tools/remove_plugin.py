import os
import re
wsl_home = r'\\wsl.localhost\Ubuntu-22.04\home\emre'
path = os.path.join(wsl_home, 'ardupilot_gazebo', 'models', 'zephyr_with_ardupilot', 'model.sdf')
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# Remove the Ignition Gazebo plugin that throws the scary but harmless error in Gazebo Classic
text = re.sub(r'<plugin filename="gz-sim-joint-state-publisher-system".*?</plugin>', '', text, flags=re.DOTALL)

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Removed incompatible plugin!")
