import os
import re
wsl_home = r'\\wsl.localhost\Ubuntu-22.04\home\emre'
path = os.path.join(wsl_home, 'ardupilot_gazebo', 'models', 'zephyr', 'model.sdf')
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# Replace the mesh collision with a perfectly sized and oriented BOX to stop EKF vibration
clean_collision = """      <collision name="body_collision">
        <pose>0 0 -0.05 0 0 0</pose>
        <geometry>
          <box>
            <size>1.2 0.5 0.1</size>
          </box>
        </geometry>
        <surface>
          <friction>
            <ode>
              <mu>0.05</mu>
              <mu2>0.5</mu2>
              <fdir1>1 0 0</fdir1>
            </ode>
          </friction>
        </surface>
      </collision>"""

text = re.sub(r'<collision name="body_collision">.*?</collision>', clean_collision, text, flags=re.DOTALL)

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Applied anti-vibration box collision!")
