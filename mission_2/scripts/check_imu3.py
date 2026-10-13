file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\zephyr_with_ardupilot\model.sdf'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()
lines = text.split('\n')
for i, line in enumerate(lines):
    if 'imuName' in line:
        for j in range(i-2, min(i+5, len(lines))):
            print(lines[j])
