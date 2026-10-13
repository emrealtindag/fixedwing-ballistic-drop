filepath = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\techpod_with_ardupilot\techpod.sdf'
with open(filepath, 'r') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if '<link name="techpod/imu_link">' in line:
        # insert sensor right after the link declaration
        sensor_xml = """      <sensor name="imu_sensor" type="imu">
        <pose>0 0 0 3.141593 0 0</pose>
        <always_on>1</always_on>
        <update_rate>1000.0</update_rate>
      </sensor>\n"""
        lines.insert(i + 1, sensor_xml)
        break

with open(filepath, 'w', newline='\n') as f:
    f.writelines(lines)
