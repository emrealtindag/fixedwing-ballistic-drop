import re

with open('/home/emre/ardupilot_gazebo/models/techpod_with_ardupilot/techpod.sdf', 'r') as f:
    content = f.read()

# Add propeller thrust plugins if not present
thrust_plugins = '''
    <!-- propeller_blade_1 -->
    <plugin name=" liftdrag_prop_1 filename=libLiftDragPlugin.so>
