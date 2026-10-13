import re

# 1. Update World File Spawn Height
world_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\worlds\iris_arducopter_runway.world'
with open(world_path, 'r', encoding='utf-8') as f:
    world_text = f.read()

world_text = world_text.replace('<pose>0 0 0.5 0 0 0</pose>', '<pose>0 0 1.2 0 0 0</pose>')
with open(world_path, 'w', encoding='utf-8') as f:
    f.write(world_text)


# 2. Update Base Model (Zephyr)
base_sdf_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\zephyr\model.sdf'
with open(base_sdf_path, 'r', encoding='utf-8') as f:
    base_text = f.read()

# Add <self_collide>false</self_collide>
if '<self_collide>' not in base_text:
    base_text = base_text.replace('<model name="zephyr">', '<model name="zephyr">\n    <self_collide>false</self_collide>')
    base_text = base_text.replace("<model name='zephyr'>", "<model name='zephyr'>\n    <self_collide>false</self_collide>")

# Fix Propeller Inertia
# Original: <mass>0.05</mass> -> 0.1
# <ixx>0.000367571</ixx> -> 0.001
# <iyy>0.00036985</iyy> -> 0.001
# <izz>3.187e-06</izz> -> 0.001
# We'll just replace the entire inertial block for propeller
propeller_inertial = """<inertial>
        <mass>0.1</mass>
        <inertia>
          <ixx>0.001</ixx>
          <ixy>0</ixy>
          <iyy>0.001</iyy>
          <ixz>0</ixz>
          <iyz>0</iyz>
          <izz>0.001</izz>
        </inertia>
      </inertial>"""
base_text = re.sub(r'<link name="propeller">[\s\S]*?<visual', '<link name="propeller">\n      <pose>0 0.07 0.008 0 1.5708 0</pose>\n      ' + propeller_inertial + '\n      <visual', base_text)

# Remove propeller collision boxes
base_text = re.sub(r'<collision name="blade1">[\s\S]*?</collision>', '', base_text)
base_text = re.sub(r'<collision name="blade2">[\s\S]*?</collision>', '', base_text)

with open(base_sdf_path, 'w', encoding='utf-8') as f:
    f.write(base_text)


# 3. Update Main Model (zephyr_with_ardupilot)
main_sdf_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\zephyr_with_ardupilot\model.sdf'
with open(main_sdf_path, 'r', encoding='utf-8') as f:
    main_text = f.read()

if '<self_collide>' not in main_text:
    main_text = main_text.replace('<model name="zephyr_with_ardupilot">', '<model name="zephyr_with_ardupilot">\n    <self_collide>false</self_collide>')

with open(main_sdf_path, 'w', encoding='utf-8') as f:
    f.write(main_text)

print("All physical ODE glitch fixes applied!")
