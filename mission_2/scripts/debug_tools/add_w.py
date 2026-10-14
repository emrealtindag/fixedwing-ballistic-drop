file_path = r'\\wsl.localhost\Ubuntu-22.04\home\emre\run_drone.sh'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

if '-w' not in text:
    text = text.replace('sim_vehicle.py -v', 'sim_vehicle.py -w -v')
    with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    print("Added -w to run_drone.sh")
else:
    print("-w already there")
