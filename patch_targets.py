import os

# 1. Weaken the thrust in techpod.sdf so it doesn't fly at 50 m/s
sdf_path = '/home/emre/ardupilot_gazebo/models/techpod_with_ardupilot/techpod.sdf'
if os.path.exists(sdf_path):
    with open(sdf_path, 'r') as f:
        content = f.read()
    
    # Replace area 0.02 with 0.005 to reduce thrust by 4x
    content = content.replace('<area>0.02</area>', '<area>0.005</area>')
    
    with open(sdf_path, 'w') as f:
        f.write(content)
    print("Weakened thrust in techpod.sdf")

# 2. Add Red and Blue targets to the world
world_path = '/home/emre/ardupilot_gazebo/worlds/teknofest_world.world'
if os.path.exists(world_path):
    with open(world_path, 'r') as f:
        world_content = f.read()
    
    targets = """
    <!-- BLUE SQUARE TARGET 1 -->
    <model name="blue_target_1">
      <static>true</static>
      <pose>0 150 0.1 0 0 0</pose>
      <link name="link">
        <visual name="visual">
          <geometry>
            <box><size>4 4 0.1</size></box>
          </geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>Gazebo/Blue</name>
            </script>
          </material>
        </visual>
      </link>
    </model>

    <!-- RED SQUARE TARGET 1 -->
    <model name="red_target_1">
      <static>true</static>
      <pose>0 300 0.1 0 0 0</pose>
      <link name="link">
        <visual name="visual">
          <geometry>
            <box><size>4 4 0.1</size></box>
          </geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>Gazebo/Red</name>
            </script>
          </material>
        </visual>
      </link>
    </model>
    
    <!-- BLUE SQUARE TARGET 2 -->
    <model name="blue_target_2">
      <static>true</static>
      <pose>50 450 0.1 0 0 0</pose>
      <link name="link">
        <visual name="visual">
          <geometry>
            <box><size>4 4 0.1</size></box>
          </geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>Gazebo/Blue</name>
            </script>
          </material>
        </visual>
      </link>
    </model>

    <!-- RED SQUARE TARGET 2 -->
    <model name="red_target_2">
      <static>true</static>
      <pose>-50 600 0.1 0 0 0</pose>
      <link name="link">
        <visual name="visual">
          <geometry>
            <box><size>4 4 0.1</size></box>
          </geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>Gazebo/Red</name>
            </script>
          </material>
        </visual>
      </link>
    </model>
"""
    if "blue_target_1" not in world_content:
        world_content = world_content.replace('</world>', targets + '\n  </world>')
        with open(world_path, 'w') as f:
            f.write(world_content)
        print("Added targets to teknofest_world.world")
    else:
        print("Targets already exist in world")
