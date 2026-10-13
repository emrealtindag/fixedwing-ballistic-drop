import re

world_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\worlds\iris_arducopter_runway.world'
with open(world_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Replace the nested model with a direct include
nested_model = """    <model name="iris_demo">
      <pose>0 0 1.2 0 0 0</pose>
      <include>
        <uri>model://skywalker_x8</uri>
      </include>
    </model>"""

direct_include = """    <include>
      <uri>model://skywalker_x8</uri>
      <pose>0 0 1.2 0 0 0</pose>
      <name>iris_demo</name>
    </include>"""

text = text.replace(nested_model, direct_include)

with open(world_path, 'w', encoding='utf-8') as f:
    f.write(text)

print("Un-nested the model in the world file to prevent '::' ROS 2 crashes!")
