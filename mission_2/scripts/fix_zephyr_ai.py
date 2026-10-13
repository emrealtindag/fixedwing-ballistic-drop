import re

file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\zephyr_with_ardupilot\model.sdf'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. SDF Version
text = text.replace("<sdf version='1.9'>", "<sdf version='1.7'>")
text = text.replace('<sdf version="1.9">', '<sdf version="1.7">')

# 2. Unique LiftDrag plugins
count = 1
def replace_liftdrag(match):
    global count
    res = f"<plugin name='liftdrag_{count}' filename='libLiftDragPlugin.so'>"
    count += 1
    return res

text = re.sub(r'<plugin name=\'liftdrag\' filename=\'libLiftDragPlugin.so\'>', replace_liftdrag, text)

# 3. Propeller Throttle Min/Max (Fixing the backwards spin when disarmed)
# Find the control channel 2 block
text = re.sub(
    r'<control channel=\'2\'>.*?<servo_min>1100</servo_min>.*?<servo_max>1900</servo_max>',
    r'<control channel=\'2\'>\n      <jointName>zephyr_with_ardupilot::zephyr::propeller_joint</jointName>\n      <useForce>1</useForce>\n      <multiplier>838</multiplier>\n      <offset>0</offset>\n      <servo_min>1000</servo_min>\n      <servo_max>2000</servo_max>',
    text, flags=re.DOTALL
)

# 4. Fix IMU orientation parsing bug (Gazebo 11 ignores degrees='1')
# 180 deg = 3.14159 rad, 90 deg = 1.5708 rad, -90 deg = -1.5708 rad
text = text.replace("<modelXYZToAirplaneXForwardZDown degrees='1'>0 0 0 180 0 -90</modelXYZToAirplaneXForwardZDown>", "<modelXYZToAirplaneXForwardZDown>0 0 0 3.14159 0 -1.5708</modelXYZToAirplaneXForwardZDown>")
text = text.replace("<gazeboXYZToNED degrees='1'>0 0 0 180 0 90</gazeboXYZToNED>", "<gazeboXYZToNED>0 0 0 3.14159 0 1.5708</gazeboXYZToNED>")

# Clean up JointStatePublisher plugin error
text = re.sub(r'<plugin name=\'gz::sim::systems::JointStatePublisher\' filename=\'gz-sim-joint-state-publisher-system\'/>', '', text)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Applied all fixes to zephyr_with_ardupilot SDF.")
