import os

world_path = os.path.expanduser('~/ardupilot_gazebo/worlds/iris_arducopter_runway.world')
with open(world_path, 'r') as f:
    content = f.read()

content = content.replace('model://skywalker_x8', 'model://cessna_with_ardupilot')
content = content.replace('model://zephyr_with_ardupilot', 'model://cessna_with_ardupilot')

with open(world_path, 'w') as f:
    f.write(content)
print("World patched")
