import xml.etree.ElementTree as ET

tree = ET.parse('models/cessna_with_ardupilot/model.sdf')
root = tree.getroot()
model = root.find('model')
body = model.find("link[@name='body']")

camera_xml = """
<sensor name="camera_front" type="camera">
  <pose>2.5 0 0.8 0 0 0</pose>
  <camera>
    <horizontal_fov>1.047</horizontal_fov>
    <image>
      <width>640</width>
      <height>480</height>
      <format>R8G8B8</format>
    </image>
    <clip>
      <near>0.1</near>
      <far>1000</far>
    </clip>
  </camera>
  <always_on>1</always_on>
  <update_rate>30</update_rate>
  <visualize>true</visualize>
  <plugin name="camera_plugin" filename="libgazebo_ros_camera.so">
    <alwaysOn>true</alwaysOn>
    <imageTopicName>/camera/image_raw</imageTopicName>
    <cameraInfoTopicName>/camera/camera_info</cameraInfoTopicName>
    <updateRate>30.0</updateRate>
    <cameraName>front_camera</cameraName>
    <frameName>camera_link</frameName>
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

cam_sensor = ET.fromstring(camera_xml)
body.append(cam_sensor)

tree.write('models/cessna_with_ardupilot/model.sdf', encoding='utf-8', xml_declaration=True)
print("Camera added successfully")
