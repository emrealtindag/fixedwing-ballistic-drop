import re

file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\zephyr_with_ardupilot\model.sdf'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

camera_xml = """
    <!-- FIXED-WING DOWNWARD TEKNOFEST CAMERA -->
    <link name="downward_camera_link">
      <pose>0 0 -0.15 0 1.134 0</pose>
      <inertial>
        <mass>0.001</mass>
        <inertia>
          <ixx>0.00001</ixx>
          <iyy>0.00001</iyy>
          <izz>0.00001</izz>
        </inertia>
      </inertial>
      <sensor name="downward_camera" type="camera">
        <camera>
          <horizontal_fov>1.085</horizontal_fov>
          <image>
            <width>640</width>
            <height>480</height>
            <format>R8G8B8</format>
          </image>
          <clip>
            <near>0.1</near>
            <far>100</far>
          </clip>
        </camera>
        <always_on>1</always_on>
        <update_rate>15</update_rate>
        <visualize>true</visualize>
        <plugin name="camera_controller" filename="libgazebo_ros_camera.so">
          <ros>
            <namespace>/</namespace>
            <remapping>~/image_raw:=downward_camera/image_raw</remapping>
            <remapping>~/camera_info:=downward_camera/camera_info</remapping>
          </ros>
          <frame_name>downward_camera_link</frame_name>
        </plugin>
      </sensor>
    </link>
    <joint name="camera_joint" type="fixed">
      <parent>zephyr::wing</parent>
      <child>downward_camera_link</child>
    </joint>
"""

if 'downward_camera_link' not in text:
    text = text.replace('</model>', camera_xml + '\n  </model>')
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print("Camera added to zephyr_with_ardupilot!")
else:
    print("Camera already exists.")
