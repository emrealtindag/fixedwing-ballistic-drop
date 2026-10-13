import re
file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\zephyr\model.sdf'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Replace mu 1.0 with 0.0 to act like wheels
text = re.sub(r'<mu>1\.0</mu>', '<mu>0.0</mu>', text)
text = re.sub(r'<mu2>1\.0</mu2>', '<mu2>0.0</mu2>', text)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Friction set to 0.0 (simulating frictionless wheels)")
