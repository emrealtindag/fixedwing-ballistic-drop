file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\iris_with_ardupilot\model.sdf'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Change Z from -0.05 to -0.15 to ensure it clears the bottom of the drone body
text = text.replace('<pose>0 0 -0.05 0 1.5707 0</pose>', '<pose>0 0 -0.15 0 1.5707 0</pose>')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
