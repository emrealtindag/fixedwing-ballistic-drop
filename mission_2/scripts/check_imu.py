file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\zephyr\model.sdf'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()
lines = text.split('\n')
for i, line in enumerate(lines):
    if 'type="imu"' in line:
        for j in range(i, min(i+15, len(lines))):
            print(lines[j])
