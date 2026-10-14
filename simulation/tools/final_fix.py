import os

wsl_home = r'\\wsl.localhost\Ubuntu-22.04\home\emre'

# 1. Fix mav.parm - add TKOFF_THR_MINACC fix and ensure TRIM correct
parm_path = os.path.join(wsl_home, 'mav.parm')
with open(parm_path, 'r', encoding='utf-8') as f:
    parm = f.read()

lines = parm.splitlines()
new_lines = []
for line in lines:
    if 'TRIM_THROTTLE' in line:
        new_lines.append('TRIM_THROTTLE    0')
    elif 'TKOFF_THR_MINACC' in line:
        new_lines.append('TKOFF_THR_MINACC 100.000000')
    elif 'TKOFF_THR_IDLE' in line:
        new_lines.append('TKOFF_THR_IDLE   0')
    else:
        new_lines.append(line)
with open(parm_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(new_lines))
print("Fixed mav.parm")

# 2. Fix teknofest_world.world - spawn 1m high
world_path = os.path.join(wsl_home, 'ardupilot_gazebo', 'worlds', 'teknofest_world.world')
with open(world_path, 'r', encoding='utf-8') as f:
    world = f.read()

import re
# Change spawn pose height to 1m
world = re.sub(r'(<model name="zephyr_with_ardupilot">\s*<pose>[\d\. ]+)</pose>', 
               lambda m: m.group(0).rsplit('>', 1)[0].rsplit(' ', 1)[0] + ' 1 0 0 0</pose>',
               world)
with open(world_path, 'w', encoding='utf-8') as f:
    f.write(world)
print("Fixed world spawn height")

print("ALL DONE")
