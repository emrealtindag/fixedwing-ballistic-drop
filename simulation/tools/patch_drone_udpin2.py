filepath = r'\\wsl.localhost\Ubuntu-22.04\home\emre\run_drone.sh'
with open(filepath, 'r') as f:
    content = f.read()

content = content.replace('--out udpin:0.0.0.0:14550 ', '')
content = content.replace('--mavproxy-args="--streamrate=10"', '--mavproxy-args="--streamrate=10 --out udpin:0.0.0.0:14550"')

with open(filepath, 'w', newline='\n') as f:
    f.write(content)
