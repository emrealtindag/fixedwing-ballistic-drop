import urllib.request
import os

base_url = "https://raw.githubusercontent.com/osrf/gazebo_models/main/zephyr_delta_wing/"
files = ["model.config", "model.sdf"]
out_dir = r"\\wsl.localhost\Ubuntu-22.04\home\emre\.gazebo\models\zephyr_delta_wing"

os.makedirs(out_dir, exist_ok=True)
for f in files:
    try:
        urllib.request.urlretrieve(base_url + f, os.path.join(out_dir, f))
        print(f"Downloaded {f} from main")
    except:
        pass
