file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\iris_with_ardupilot\model.sdf'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

safe_camera = """
    <link name="camera_link">
      <pose>0 0 -0.15 0 1.5707 0</pose>
      <inertial>
        <mass>0.001</mass>
        <inertia>
          <ixx>0.00001</ixx>
          <iyy>0.00001</iyy>
          <izz>0.00001</izz>
        </inertia>
      </inertial>
      <visual name="visual">
        <geometry><cylinder><radius>0.02</radius><length>0.02</length></cylinder></geometry>
        <material><ambient>0 0 0 1</ambient></material>
      </visual>
      <sensor name="downward_camera" type="camera">
        <always_on>true</always_on>
        <update_rate>30.0</update_rate>
        <camera>
          <horizontal_fov>1.085</horizontal_fov>
          <image>
            <width>640</width>
            <height>480</height>
            <format>R8G8B8</format>
          </image>
          <clip>
            <near>0.05</near>
            <far>1000</far>
          </clip>
        </camera>
        <plugin name="camera_controller" filename="libgazebo_ros_camera.so">
          <ros>
            <remapping>image_raw:=camera/image_raw</remapping>
          </ros>
          <camera_name>downward_camera</camera_name>
          <frame_name>camera_link</frame_name>
        </plugin>
      </sensor>
    </link>
    <joint name="camera_joint" type="fixed">
      <parent>iris::base_link</parent>
      <child>camera_link</child>
    </joint>
  </model>
"""

# Only replace the last occurrence of </model>
text = text[:text.rfind('  </model>')] + safe_camera

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
