import os
import re
wsl_home = r'\\wsl.localhost\Ubuntu-22.04\home\emre'
path = os.path.join(wsl_home, 'ardupilot_gazebo', 'models', 'zephyr', 'model.sdf')
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# Add max_vel and min_depth to completely stop ODE micro-vibrations (which cause phantom aerodynamic lift)
contact_params = """
            <ode>
              <mu>0.1</mu>
              <mu2>0.1</mu2>
              <fdir1>1 0 0</fdir1>
              <slip1>0.0</slip1>
              <slip2>0.0</slip2>
            </ode>
          </friction>
          <contact>
            <ode>
              <kp>100000.0</kp>
              <kd>100.0</kd>
              <max_vel>0.1</max_vel>
              <min_depth>0.005</min_depth>
            </ode>
          </contact>
"""
text = re.sub(r'<ode>\s*<mu>0.1</mu>\s*<mu2>0.1</mu2>\s*<fdir1>1 0 0</fdir1>\s*</ode>\s*</friction>', contact_params, text, flags=re.DOTALL)

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Applied soft contact parameters!")
