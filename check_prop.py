import time
import subprocess

for i in range(5):
    result = subprocess.run(["wsl", "-e", "bash", "-c", "gz model -i -m zephyr_with_ardupilot | grep -A 5 propeller_joint"], capture_output=True, text=True)
    print(result.stdout)
    time.sleep(1)
