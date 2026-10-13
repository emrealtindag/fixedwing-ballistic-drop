file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\run_sim.sh'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

if 'setup.bash' not in text:
    text = text.replace('#!/bin/bash', '#!/bin/bash\nsource /opt/ros/humble/setup.bash\nsource /usr/share/gazebo/setup.sh\n')
    with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
