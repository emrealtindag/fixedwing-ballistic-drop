file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\iris_with_ardupilot\model.sdf'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Move camera 0.5m forward and 0.2m down to completely escape any drone geometry
text = text.replace('<pose>0 0 -0.15 0 1.5707 0</pose>', '<pose>0.5 0 -0.2 0 1.5707 0</pose>')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
