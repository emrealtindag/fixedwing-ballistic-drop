file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\zephyr\model.sdf'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Replace degrees="true" and convert to radians
# <pose degrees="true">0 0.07 0.008 0 90 0</pose> -> <pose>0 0.07 0.008 0 1.5708 0</pose>
text = text.replace('<pose degrees="true">0 0.07 0.008 0 90 0</pose>', '<pose>0 0.07 0.008 0 1.5708 0</pose>')
# <pose degrees="true">0 0 0 180 0 -90</pose> -> <pose>0 0 0 3.14159 0 -1.5708</pose>
text = text.replace('<pose degrees="true">0 0 0 180 0 -90</pose>', '<pose>0 0 0 3.14159 0 -1.5708</pose>')

# Also fix the SDF version just in case
text = text.replace('<sdf version="1.9">', '<sdf version="1.7">')
text = text.replace("<sdf version='1.9'>", "<sdf version='1.7'>")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Fixed base Zephyr model!")
