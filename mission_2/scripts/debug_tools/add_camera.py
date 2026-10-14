file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\skywalker_x8\model.sdf'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

camera_xml = """
    <!-- FIXED-WING DOWNWARD TEKNOFEST CAMERA -->
    <link name="downward_camera">
      <!-- 25 degree pitch forward: 0 0 0 0 0.436332 0 (0.436 rad = 25 deg) -->
      <!-- We will just point it straight down with a slight pitch if needed, but let's do 0 0 -0.15 0 1.5707 0 first for testing, actually 25 deg pitch from down is 1.5707 - 0.4363 = 1.134 rad -->
      <pose>0 0 -0.15 0 1.134 0</pose>
      <mass>0.001</mass>
      <inertial>
        <mass>0.001</mass>
        <inertia>
          <ixx>0.00001</ixx>
          <iyy>0.00001</iyy>
          <izz>0.00001</izz>
        </inertia>
      </inertial>
      <sensor name="camera" type="camera">
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
          </ros>
          <camera_name>downward_camera</camera_name>
          <frame_name>downward_camera</frame_name>
        </plugin>
      </sensor>
    </link>
    <joint name="camera_joint" type="fixed">
      <parent>base_link</parent>
      <child>downward_camera</child>
    </joint>
"""

# Insert before </model>
if '<!-- FIXED-WING DOWNWARD TEKNOFEST CAMERA -->' not in text:
    text = text.replace('</model>', camera_xml + '\n  </model>')
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print("Camera added to Skywalker X8!")
else:
    print("Camera already exists.")
