import re
import subprocess
import os

filepath = r'\\wsl.localhost\Ubuntu-22.04\home\emre\aerointel_ws\ros2_udp_bridge.py'
if os.path.exists(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Get the WSL host IP by reading resolv.conf
    resolv_path = r'\\wsl.localhost\Ubuntu-22.04\etc\resolv.conf'
    ip = '127.0.0.1'
    if os.path.exists(resolv_path):
        with open(resolv_path, 'r') as f:
            for line in f:
                if 'nameserver' in line:
                    ip = line.split()[1].strip()
                    break

    content = re.sub(r'self\.target_ip\s*=\s*[\'"].*?[\'"]', f'self.target_ip = "{ip}"', content)
    with open(filepath, 'w') as f:
        f.write(content)
    print(f"Patched bridge IP to {ip}")
else:
    print("Bridge file not found")
