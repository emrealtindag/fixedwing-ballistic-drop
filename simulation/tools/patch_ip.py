import re
filepath = r'\\wsl.localhost\Ubuntu-22.04\home\emre\aerointel_ws\ros2_udp_bridge.py'
with open(filepath, 'r') as f:
    content = f.read()
content = re.sub(r'self\.target_ip\s*=\s*[\'"].*?[\'"]', 'self.target_ip = "172.31.176.1"', content)
with open(filepath, 'w') as f:
    f.write(content)
