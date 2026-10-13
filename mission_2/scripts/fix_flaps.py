# 1. Update Base Model Flap Inertias
base_sdf = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\zephyr\model.sdf'
with open(base_sdf, 'r', encoding='utf-8') as f:
    text = f.read()

# Make the flaps heavier so ODE doesn't explode
import re
text = re.sub(r'<ixx>0\.000102319</ixx>', '<ixx>0.01</ixx>', text)
text = re.sub(r'<iyy>0\.00334417</iyy>', '<iyy>0.01</iyy>', text)
text = re.sub(r'<izz>0\.003446072</izz>', '<izz>0.01</izz>', text)

with open(base_sdf, 'w', encoding='utf-8') as f:
    f.write(text)

# 2. Lower p_gain in Main Model for the flaps
main_sdf = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\zephyr_with_ardupilot\model.sdf'
with open(main_sdf, 'r', encoding='utf-8') as f:
    main_text = f.read()

main_text = main_text.replace('<p_gain>10.0</p_gain>', '<p_gain>1.0</p_gain>')
main_text = main_text.replace('<d_gain>0</d_gain>', '<d_gain>0.1</d_gain>') # Add a little damping

with open(main_sdf, 'w', encoding='utf-8') as f:
    f.write(main_text)

print("Fixed Flap PID and Inertia explosion risk!")
