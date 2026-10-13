import os
import re
wsl_home = r'\\wsl.localhost\Ubuntu-22.04\home\emre'
path = os.path.join(wsl_home, 'ardupilot_gazebo', 'worlds', 'teknofest_world.world')
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# Add a massive green grass visual to the ground plane so the user can see it
grass_visual = """
        <visual name="grass">
          <pose>0 0 0 0 0 0</pose>
          <cast_shadows>false</cast_shadows>
          <geometry>
            <plane>
              <normal>0 0 1</normal>
              <size>5000 5000</size>
            </plane>
          </geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>Gazebo/Grass</name>
            </script>
          </material>
        </visual>
"""
if 'name="grass"' not in text:
    text = text.replace('</collision>', '</collision>' + grass_visual)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
print("Added massive grass ground visual!")
