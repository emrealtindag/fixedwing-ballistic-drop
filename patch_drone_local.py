filepath = r'\\wsl.localhost\Ubuntu-22.04\home\emre\run_drone.sh'
with open(filepath, 'r') as f:
    content = f.read()
content = content.replace('IP="172.31.176.1"', 'IP="127.0.0.1"')
with open(filepath, 'w', newline='\n') as f:
    f.write(content)
