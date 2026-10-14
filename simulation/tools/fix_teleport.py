import os
wsl_home = r'\\wsl.localhost\Ubuntu-22.04\home\emre'
path = os.path.join(wsl_home, 'run_drone.sh')
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('--console -l 0,0,0,0', '--console')
with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Reverted run_drone.sh to default location (CMAC)")
