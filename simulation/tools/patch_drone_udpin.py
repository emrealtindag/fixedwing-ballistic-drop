filepath = r'\\wsl.localhost\Ubuntu-22.04\home\emre\run_drone.sh'
with open(filepath, 'r') as f:
    content = f.read()
content = content.replace('--out 127.0.0.1:14550', '--out udpin:0.0.0.0:14550')
content = content.replace('--out $IP:14550', '--out udpin:0.0.0.0:14550')
content = content.replace('IP="127.0.0.1"', '')
with open(filepath, 'w', newline='\n') as f:
    f.write(content)
