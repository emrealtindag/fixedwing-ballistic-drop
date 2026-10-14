file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\run_drone.sh'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('ArduCopter', 'ArduPlane')
text = text.replace('gazebo-iris', 'gazebo-zephyr')

with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(text)
print("run_drone.sh updated for ArduPlane and gazebo-zephyr.")
