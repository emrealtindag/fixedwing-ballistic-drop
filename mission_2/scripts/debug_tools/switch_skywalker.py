import re

file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\skywalker_x8\model.sdf'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Fix p_gain explosion
text = text.replace('<p_gain>10.0</p_gain>', '<p_gain>1.0</p_gain>')
text = text.replace('<d_gain>0</d_gain>', '<d_gain>0.1</d_gain>')

# Add self_collide false to prevent glitching
if '<self_collide>' not in text:
    text = text.replace('<model name="skywalker_x8">', '<model name="skywalker_x8">\n    <self_collide>false</self_collide>')

# Fix wheel friction so it can take off smoothly (like we did for zephyr)
if '<friction>' not in text:
    friction_xml = """<surface><friction><ode><mu>0.02</mu><mu2>0.02</mu2></ode></friction></surface>"""
    text = re.sub(r'(<collision name="base_link_collision">[\s\S]*?</geometry>\n)', r'\1        ' + friction_xml + '\n', text)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

# Now switch the world to skywalker
world_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\worlds\iris_arducopter_runway.world'
with open(world_path, 'r', encoding='utf-8') as f:
    world_text = f.read()

world_text = world_text.replace('<uri>model://zephyr_with_ardupilot</uri>', '<uri>model://skywalker_x8</uri>')
world_text = world_text.replace('<uri>model://zephyr</uri>', '<uri>model://skywalker_x8</uri>')

with open(world_path, 'w', encoding='utf-8') as f:
    f.write(world_text)

print("Skywalker X8 patched and integrated!")
