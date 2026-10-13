with open(r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\techpod_with_ardupilot\techpod.sdf', 'r') as f:
    lines = f.readlines()

in_plugin = False
for line in lines:
    if '<plugin name="ardupilot' in line or '<plugin name="Ardu' in line:
        in_plugin = True
    if in_plugin:
        print(line.strip())
    if in_plugin and '</plugin>' in line:
        break
