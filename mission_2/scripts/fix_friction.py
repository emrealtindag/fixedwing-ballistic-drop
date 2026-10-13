import re

file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\zephyr\model.sdf'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('<mu>100.0</mu>', '<mu>0.8</mu>')
text = text.replace('<mu2>50.0</mu2>', '<mu2>0.8</mu2>')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Friction lowered from superglue (100) to normal tarmac (0.8)")
