import os

sdf_path = '/home/emre/ardupilot_gazebo/models/cessna_with_ardupilot/model.sdf'
with open(sdf_path, 'r') as f:
    content = f.read()

downward_cam = """
    <sensor name="camera_downward" type="camera">
      <!-- Pitch is 1.570796 radians (90 degrees) to face exactly downwards -->
      <pose>0.5 0 -0.2 0 1.570796 0</pose>
      <camera>
        <horizontal_fov>1.047</horizontal_fov>
        <image>
          <width>640</width>
          <height>480</height>
        </image>
        <clip>
          <near>0.1</near>
          <far>1000</far>
        </clip>
      </camera>
      <always_on>1</always_on>
      <update_rate>30</update_rate>
      <visualize>true</visualize>
      <plugin name="camera_down_plugin" filename="libgazebo_ros_camera.so">
        <alwaysOn>true</alwaysOn>
        <imageTopicName>/camera_down/image_raw</imageTopicName>
        <cameraInfoTopicName>/camera_down/camera_info</cameraInfoTopicName>
        <updateRate>30.0</updateRate>
        <cameraName>downward_camera</cameraName>
        <frameName>camera_down_link</frameName>
        <CxPrime>320.5</CxPrime>
        <Cx>320.5</Cx>
        <Cy>240.5</Cy>
        <hackBaseline>0</hackBaseline>
        <focalLength>277.19</focalLength>
        <distortionK1>0.0</distortionK1>
        <distortionK2>0.0</distortionK2>
        <distortionK3>0.0</distortionK3>
        <distortionT1>0.0</distortionT1>
        <distortionT2>0.0</distortionT2>
      </plugin>
    </sensor>
"""

# Insert the downward camera right before the lidar_down sensor or before </link>
if '<sensor name="camera_downward"' not in content:
    content = content.replace('</link>', downward_cam + '\n      </link>', 1)
    with open(sdf_path, 'w') as f:
        f.write(content)
    print("Downward camera added!")
else:
    print("Downward camera already exists.")
