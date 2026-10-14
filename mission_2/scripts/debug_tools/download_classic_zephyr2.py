import urllib.request
import os

url = "https://raw.githubusercontent.com/ArduPilot/ardupilot_gazebo/master/models/zephyr/meshes/wing.dae"
out_path = r"\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\zephyr\meshes\wing.dae"

os.makedirs(os.path.dirname(out_path), exist_ok=True)
try:
    urllib.request.urlretrieve(url, out_path)
    print("Downloaded wing.dae")
except Exception as e:
    print("Failed to download wing.dae", e)

url_png = "https://raw.githubusercontent.com/ArduPilot/ardupilot_gazebo/master/models/zephyr/materials/textures/wing_texture.png"
out_path_png = r"\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models\zephyr\materials\textures\wing_texture.png"
os.makedirs(os.path.dirname(out_path_png), exist_ok=True)
try:
    urllib.request.urlretrieve(url_png, out_path_png)
    print("Downloaded wing_texture.png")
except Exception as e:
    print("Failed to download wing_texture.png", e)

