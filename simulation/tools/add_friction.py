import os

sdf_path = '/home/emre/ardupilot_gazebo/models/techpod_with_ardupilot/techpod.sdf'
with open(sdf_path, 'r') as f:
    content = f.read()

# Replace the contact block for base_link_collision to add friction
old_str = """        <surface>
          <contact>
            <ode>
              <max_vel>10</max_vel>
              <min_depth>0.01</min_depth>
            </ode>
          </contact>
        </surface>"""

new_str = """        <surface>
          <contact>
            <ode>
              <max_vel>10</max_vel>
              <min_depth>0.01</min_depth>
            </ode>
          </contact>
          <friction>
            <ode>
              <mu>0.05</mu>
              <mu2>0.05</mu2>
            </ode>
          </friction>
        </surface>"""

if old_str in content:
    content = content.replace(old_str, new_str)
    with open(sdf_path, 'w') as f:
        f.write(content)
    print("Friction added successfully.")
else:
    print("Could not find the target string to replace.")
