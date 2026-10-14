file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\worlds\iris_arducopter_runway.world'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('<uri>model://skywalker_x8</uri>', '<uri>model://zephyr_with_ardupilot</uri>')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
print("World updated to spawn zephyr_with_ardupilot.")
