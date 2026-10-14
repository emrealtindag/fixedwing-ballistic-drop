import os
import re
wsl_home = r'\\wsl.localhost\Ubuntu-22.04\home\emre'
path = os.path.join(wsl_home, 'ardupilot_gazebo', 'models', 'zephyr', 'model.sdf')
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# Restore the original mesh collision with proper friction
clean_collision = """      <collision name="body_collision">
        <geometry>
          <mesh>
            <uri>model://zephyr/meshes/wing.dae</uri>
            <submesh>
              <name>Wing</name>
              <center>true</center>
            </submesh>
          </mesh>
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
print("Restored original mesh collision with sled friction!")
