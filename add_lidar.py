import xml.etree.ElementTree as ET

tree = ET.parse('models/cessna_with_ardupilot/model.sdf')
root = tree.getroot()
model = root.find('model')
body = model.find("link[@name='body']")

lidar_xml = """
<sensor name="lidar_down" type="ray">
  <pose>0 0 -0.5 0 1.570796 0</pose> <!-- Pointing straight down -->
  <visualize>true</visualize>
  <update_rate>10</update_rate>
  <ray>
    <scan>
      <horizontal>
        <samples>1</samples>
        <resolution>1</resolution>
        <min_angle>0</min_angle>
        <max_angle>0</max_angle>
      </horizontal>
    </scan>
    <range>
      <min>0.1</min>
      <max>50.0</max>
      <resolution>0.01</resolution>
    </range>
  </ray>
  <plugin name="lidar_plugin" filename="libgazebo_ros_range.so">
    <topicName>/lidar/range</topicName>
    <frameName>lidar_link</frameName>
    <updateRate>10.0</updateRate>
    <radiation>infrared</radiation>
    <fov>0.01</fov>
  </plugin>
</sensor>
"""

lidar_sensor = ET.fromstring(lidar_xml)
body.append(lidar_sensor)

tree.write('models/cessna_with_ardupilot/model.sdf', encoding='utf-8', xml_declaration=True)
print("Lidar added successfully")
