file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\iris_with_ardupilot\model.sdf'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

import re
# Change pitch to 45 degrees (0.785) so it sees both ground and sky, making it obvious if it's working
text = re.sub(r'<pose>[^<]+</pose>', '<pose>0.5 0 -0.2 0 0.785 0</pose>', text)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)
