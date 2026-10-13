import re

file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\skywalker_x8\model.sdf'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Fix ROS 2 camera topic name (Remove :: which crashes rclcpp)
text = text.replace('<camera_name>skywalker_x8::downward_camera</camera_name>', '<camera_name>downward_camera</camera_name>')
text = text.replace('<frame_name>skywalker_x8::downward_camera</frame_name>', '<frame_name>downward_camera</frame_name>')

# 2. Convert Ignition plugins to Gazebo 11 Classic
text = text.replace('filename=\'gz-sim-lift-drag-system\'', 'filename=\'libLiftDragPlugin.so\'')
text = text.replace('filename="gz-sim-lift-drag-system"', 'filename="libLiftDragPlugin.so"')

# 3. Fix non-unique liftdrag names
counter = 1
while "gz::sim::systems::LiftDrag" in text:
    text = text.replace("gz::sim::systems::LiftDrag", f"liftdrag_{counter}", 1)
    counter += 1

# 4. Remove unsupported Ignition systems that crash Gazebo 11
text = re.sub(r'<plugin name=[\'"]gz::sim::systems::JointStatePublisher[\'"].*?/>', '', text, flags=re.DOTALL)
text = re.sub(r'<plugin name=[\'"]gz::sim::systems::ApplyJointForce[\'"].*?</plugin>', '', text, flags=re.DOTALL)

# 5. Fix Gazebo 11 degrees bug in ArduPilotPlugin
text = text.replace("<modelXYZToAirplaneXForwardZDown degrees='1'>0 0 0 180 0 0</modelXYZToAirplaneXForwardZDown>", 
                    "<modelXYZToAirplaneXForwardZDown>0 0 0 3.14159 0 0</modelXYZToAirplaneXForwardZDown>")
text = text.replace("<gazeboXYZToNED degrees='1'>0 0 0 180 0 90</gazeboXYZToNED>", 
                    "<gazeboXYZToNED>0 0 0 3.14159 0 1.570796</gazeboXYZToNED>")

# Ensure there's no mass tag outside inertial in the camera link
text = text.replace('</sensor>\n    <mass>0.001</mass>', '</sensor>')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

print("Skywalker X8 fixed for Gazebo 11 Classic and ROS 2!")
