import re

with open('/home/emre/ardupilot_gazebo/models/techpod_with_ardupilot/techpod.sdf', 'r') as f:
    content = f.read()

# Add propeller thrust plugins if not present
thrust_plugins = """
    <!-- propeller_blade_1 -->
    <plugin name="liftdrag_prop_1" filename="libLiftDragPlugin.so">
      <a0>0.30</a0>
      <alpha_stall>1.4</alpha_stall>
      <cla>4.2500</cla>
      <cda>0.10</cda>
      <cma>0.0</cma>
      <cla_stall>-0.025</cla_stall>
      <cda_stall>0.0</cda_stall>
      <cma_stall>0.0</cma_stall>
      <area>0.02</area>
      <air_density>1.2041</air_density>
      <cp>0 0.1 0</cp>
      <forward>0 0 -1</forward>
      <upward>1 0 0</upward>
      <link_name>rotor_puller</link_name>
    </plugin>
    <!-- propeller_blade_2 -->
    <plugin name="liftdrag_prop_2" filename="libLiftDragPlugin.so">
      <a0>0.30</a0>
      <alpha_stall>1.4</alpha_stall>
      <cla>4.2500</cla>
      <cda>0.10</cda>
      <cma>0.0</cma>
      <cla_stall>-0.025</cla_stall>
      <cda_stall>0.0</cda_stall>
      <cma_stall>0.0</cma_stall>
      <area>0.02</area>
      <air_density>1.2041</air_density>
      <cp>0 -0.1 0</cp>
      <forward>0 0 1</forward>
      <upward>1 0 0</upward>
      <link_name>rotor_puller</link_name>
    </plugin>
"""

if 'liftdrag_prop_1' not in content:
    content = content.replace('</model>', thrust_plugins + '\n  </model>')
    with open('/home/emre/ardupilot_gazebo/models/techpod_with_ardupilot/techpod.sdf', 'w') as f:
        f.write(content)
    print('Patched techpod.sdf with propeller thrust plugins!')
else:
    print('Already patched.')
