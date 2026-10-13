file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\zephyr_with_ardupilot\model.sdf'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = re.finditer(r'<control channel.*?p_gain>.*?</p_gain>', text, re.DOTALL)
for m in matches:
    print(m.group(0))
