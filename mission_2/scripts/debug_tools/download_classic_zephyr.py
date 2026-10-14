import urllib.request
import os

base_url = "https://raw.githubusercontent.com/ArduPilot/ardupilot_gazebo/master/models/"
models = {
    "zephyr": ["model.config", "model.sdf", "materials/textures/zephyr_default.png", "meshes/zephyr.dae"],
    "zephyr_with_ardupilot": ["model.config", "model.sdf"]
}
out_base = r"\\wsl.localhost\Ubuntu-22.04\home\emre\ardupilot_gazebo\models"

for model, files in models.items():
    model_dir = os.path.join(out_base, model)
    os.makedirs(model_dir, exist_ok=True)
    for f in files:
        url = base_url + model + "/" + f
        out_path = os.path.join(model_dir, os.path.normpath(f))
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        try:
            urllib.request.urlretrieve(url, out_path)
            print(f"Downloaded {model}/{f}")
        except Exception as e:
            print(f"Failed to download {model}/{f}: {e}")

