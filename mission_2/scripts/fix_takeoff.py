import re

# 1. Update Base Model Friction to simulate wheels (0.02)
base_sdf = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\zephyr\model.sdf'
with open(base_sdf, 'r', encoding='utf-8') as f:
    base_text = f.read()

base_text = base_text.replace('<mu>0.8</mu>', '<mu>0.02</mu>')
base_text = base_text.replace('<mu2>0.8</mu2>', '<mu2>0.02</mu2>')

with open(base_sdf, 'w', encoding='utf-8') as f:
    f.write(base_text)

# 2. Update Propeller to strictly STOP when disarmed
main_sdf = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\zephyr_with_ardupilot\model.sdf'
with open(main_sdf, 'r', encoding='utf-8') as f:
    main_text = f.read()

# Replace propeller servo block to clip negative values and match 1100 idle PWM
prop_regex = r'(<control channel="2">[\s\S]*?<type>VELOCITY</type>\n\s*<p_gain>0\.20</p_gain>)'
replacement = r"""<control channel="2">
        <jointName>zephyr_with_ardupilot::zephyr::propeller_joint</jointName>
        <useForce>1</useForce>
        <multiplier>838</multiplier>
        <offset>0</offset>
        <servo_min>1100</servo_min>
        <servo_max>1900</servo_max>
        <type>VELOCITY</type>
        <p_gain>0.20</p_gain>
        <cmd_min>0.0</cmd_min>
        <cmd_max>2.0</cmd_max>"""

main_text = re.sub(r'<control channel="2">[\s\S]*?<p_gain>0\.20</p_gain>', replacement, main_text)

with open(main_sdf, 'w', encoding='utf-8') as f:
    f.write(main_text)

print("Applied Wheel Friction and Absolute Propeller Stop!")
