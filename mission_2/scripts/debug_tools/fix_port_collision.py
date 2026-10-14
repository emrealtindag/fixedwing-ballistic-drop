import os

# Update run_drone.sh
file_path_sh = r'\\wsl.localhost\Ubuntu-22.04\home\emre\run_drone.sh'
with open(file_path_sh, 'r', encoding='utf-8') as f:
    text_sh = f.read()

text_sh = text_sh.replace('tcpin:0.0.0.0:5762', 'tcpin:0.0.0.0:5777')
with open(file_path_sh, 'w', encoding='utf-8', newline='\n') as f:
    f.write(text_sh)

# Update mission2_fixedwing.yaml
file_path_yaml = r'mission_2\configs\mission2_fixedwing.yaml'
with open(file_path_yaml, 'r', encoding='utf-8') as f:
    text_yaml = f.read()

text_yaml = text_yaml.replace('tcp:127.0.0.1:5762', 'tcp:127.0.0.1:5777')
with open(file_path_yaml, 'w', encoding='utf-8') as f:
    f.write(text_yaml)

print("Changed port to 5777 in both files!")
