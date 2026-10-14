import xml.etree.ElementTree as ET

sdf_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\techpod_with_ardupilot\techpod.sdf'
tree = ET.parse(sdf_path)
root = tree.getroot()
model = root.find('model')

# Remove gps and airspeed
for inc in model.findall('include'):
    uri = inc.find('uri')
    if uri is not None and ('gps' in uri.text or 'airspeed' in uri.text):
        model.remove(inc)
for joint in model.findall('joint'):
    if joint.get('name') in ['gps_joint', 'airspeed_joint']:
        model.remove(joint)

# Change libardupilot_gazebo.so to libArduPilotPlugin.so
for plugin in model.findall('plugin'):
    if plugin.get('filename') == 'libardupilot_gazebo.so':
        plugin.set('filename', 'libArduPilotPlugin.so')

# Fix sensors inside base_link
base_link = model.find("link[@name='base_link']")
if base_link is not None:
    # Remove lidar completely
    for sensor in base_link.findall('sensor'):
        if sensor.get('name') == 'lidar_down':
            base_link.remove(sensor)
        
        # Update camera ROS 2 plugin syntax
        if sensor.get('type') == 'camera':
            plugin = sensor.find('plugin')
            if plugin is not None:
                cam_name = sensor.get('name')
                topic_prefix = '/camera' if cam_name == 'camera_front' else '/downward_camera'
                
                # Clear old plugin contents
                for child in list(plugin):
                    plugin.remove(child)
                
                ros_elem = ET.SubElement(plugin, 'ros')
                ns_elem = ET.SubElement(ros_elem, 'namespace')
                ns_elem.text = '/'
                
                remap1 = ET.SubElement(ros_elem, 'remapping')
                remap1.text = f'~/image_raw:={topic_prefix}/image_raw'
                
                remap2 = ET.SubElement(ros_elem, 'remapping')
                remap2.text = f'~/camera_info:={topic_prefix}/camera_info'
                
                frame_elem = ET.SubElement(plugin, 'frame_name')
                frame_elem.text = f'{cam_name}_link'

tree.write(sdf_path, encoding='utf-8', xml_declaration=True)

# Also fix the world file plane rotation
world_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\worlds\teknofest_world.world'
with open(world_path, 'r') as f:
    wdata = f.read()

# Replace <pose>0 0 0.5 0 0 0</pose> before techpod with <pose>0 0 0.5 0 0 1.5707</pose>
wdata = wdata.replace('<pose>0 0 0.5 0 0 0</pose>\n      <uri>model://techpod_with_ardupilot</uri>', 
                      '<pose>0 0 0.5 0 0 1.5707</pose>\n      <uri>model://techpod_with_ardupilot</uri>')

with open(world_path, 'w') as f:
    f.write(wdata)

print('Fixed SDF and World')
