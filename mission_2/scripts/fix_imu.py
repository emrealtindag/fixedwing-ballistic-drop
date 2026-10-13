file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\zephyr_with_ardupilot\model.sdf'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('<modelXYZToAirplaneXForwardZDown degrees="true">0 0 0 180 0 -90</modelXYZToAirplaneXForwardZDown>', '<modelXYZToAirplaneXForwardZDown>0 0 0 3.14159 0 -1.5708</modelXYZToAirplaneXForwardZDown>')
text = text.replace('<gazeboXYZToNED degrees="true">0 0 0 180 0 90</gazeboXYZToNED>', '<gazeboXYZToNED>0 0 0 3.14159 0 1.5708</gazeboXYZToNED>')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Fixed IMU radians")
