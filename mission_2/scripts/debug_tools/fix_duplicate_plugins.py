import re

file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\zephyr_with_ardupilot\model.sdf'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

count = 1
def replace_liftdrag(match):
    global count
    res = f'<plugin name="liftdrag_{count}" filename="libLiftDragPlugin.so">'
    count += 1
    return res

text = re.sub(r'<plugin name="liftdrag" filename="libLiftDragPlugin.so">', replace_liftdrag, text)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Fixed duplicate plugin names")
