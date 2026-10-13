import os

sdf_path = '/home/emre/ardupilot_gazebo/models/techpod_with_ardupilot/techpod.sdf'

with open(sdf_path, 'r') as f:
    content = f.read()

# For blade 1 (cp 0 -0.1 0)
b1_idx = content.find('propeller_blade_1')
b2_idx = content.find('propeller_blade_2')

part1 = content[:b1_idx]
part2 = content[b1_idx:b2_idx]
part3 = content[b2_idx:]

# Swap the forwards
part2 = part2.replace('<forward>0 0 -1</forward>', '<forward>0 0 1</forward>')
part3 = part3.replace('<forward>0 0 1</forward>', '<forward>0 0 -1</forward>')

new_content = part1 + part2 + part3

with open(sdf_path, 'w') as f:
    f.write(new_content)

print("Swapped forward vectors for positive thrust!")
