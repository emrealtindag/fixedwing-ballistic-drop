file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\zephyr_with_ardupilot\model.sdf'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('<servo_min>1100</servo_min>\n        <servo_max>1900</servo_max>\n        <type>VELOCITY</type>', '<servo_min>1000</servo_min>\n        <servo_max>2000</servo_max>\n        <type>VELOCITY</type>')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Fixed Propeller Min Max")
