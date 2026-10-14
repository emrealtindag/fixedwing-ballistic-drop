import re
import os

wsl_home = r'\\wsl.localhost\Ubuntu-22.04\home\emre'
file_path = os.path.join(wsl_home, 'ardupilot_gazebo', 'models', 'zephyr', 'model.sdf')

with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Remove the landing gear hack (it's causing Gazebo ODE instability)
text = re.sub(r'<!-- INVISIBLE LANDING GEAR FOR GROUND TAKEOFF -->.*?</collision>\s*</collision>\s*</collision>', '', text, flags=re.DOTALL)
# Just in case regex fails due to exact match
text = re.sub(r'<collision name="nose_gear">.*?</collision>', '', text, flags=re.DOTALL)
text = re.sub(r'<collision name="left_gear">.*?</collision>', '', text, flags=re.DOTALL)
text = re.sub(r'<collision name="right_gear">.*?</collision>', '', text, flags=re.DOTALL)

# Set the belly friction to 0.05 so it can slide like a sled (stable, but low friction)
# And set fdir1 so it tracks straight
text = re.sub(r'<friction>.*?</friction>', '<friction><ode><mu>0.01</mu><mu2>0.5</mu2><fdir1>1 0 0</fdir1></ode></friction>', text, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

print("Restored stable sled physics!")
