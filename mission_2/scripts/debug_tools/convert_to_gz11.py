import os
import re

file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\zephyr_with_ardupilot\model.sdf'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Convert ArduPilotPlugin
text = text.replace('<plugin name="ArduPilotPlugin" filename="ArduPilotPlugin">', '<plugin name="ardupilot_plugin" filename="libArduPilotPlugin.so">')

# 2. Convert LiftDrag plugins
text = re.sub(r'<plugin filename="gz-sim-lift-drag-system"\s*name="gz::sim::systems::LiftDrag">', '<plugin name="liftdrag" filename="libLiftDragPlugin.so">', text)

# 3. Remove gz-sim-apply-joint-force-system (Gazebo 11 ArduPilot plugin applies joint forces directly)
text = re.sub(r'<plugin filename="gz-sim-apply-joint-force-system"[\s\S]*?</plugin>', '', text)

# 4. Convert JointStatePublisher (not needed for Gazebo 11 ArduPilot plugin)
text = re.sub(r'<plugin name=\'gz::sim::systems::JointStatePublisher\' filename=\'gz-sim-joint-state-publisher-system\'/>', '', text)

with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(text)
print("Converted zephyr_with_ardupilot to Gazebo 11 Classic!")
