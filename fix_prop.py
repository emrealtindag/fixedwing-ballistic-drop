import os
import re
wsl_home = r'\\wsl.localhost\Ubuntu-22.04\home\emre'
path = os.path.join(wsl_home, 'ardupilot_gazebo', 'models', 'zephyr_with_ardupilot', 'model.sdf')
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# For channel 2 (propeller), change servo_min to 1500. 
# This way, any PWM from 1100 (disarmed) to 1500 (RC trim) will result in negative or zero velocity,
# which gets clamped to 0.0 by cmd_min. The propeller will ONLY spin when PWM > 1500 (Throttle up)!
text = re.sub(r'<control channel="2">\s*<jointName>zephyr_with_ardupilot::zephyr::propeller_joint</jointName>\s*<useForce>1</useForce>\s*<multiplier>838</multiplier>\s*<offset>0</offset>\s*<servo_min>1100</servo_min>', 
              '<control channel="2">\n        <jointName>zephyr_with_ardupilot::zephyr::propeller_joint</jointName>\n        <useForce>1</useForce>\n        <multiplier>838</multiplier>\n        <offset>0</offset>\n        <servo_min>1500</servo_min>', 
              text, flags=re.DOTALL)

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Propeller idle clamp applied!")
