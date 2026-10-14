#!/bin/bash
set -e

echo "== ArduPilot Derleniyor (Plane) =="
cd ~/ardupilot
./modules/waf/waf-light configure --board sitl
./modules/waf/waf-light plane

echo "== ardupilot_gazebo Eklentisi Derleniyor (Harmonic icin) =="
cd ~/ardupilot_gazebo
mkdir -p build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DGZ_VERSION=harmonic
make -j$(nproc)

echo "== Ortam Degiskenleri Ayarlaniyor (.bashrc) =="
# Eger daha once eklenmemisse .bashrc'ye gerekli yollari ekle
if ! grep -q "GZ_SIM_SYSTEM_PLUGIN_PATH" ~/.bashrc; then
  echo "" >> ~/.bashrc
  echo "# ArduPilot Gazebo Eklentisi ve Modelleri" >> ~/.bashrc
  echo "export GZ_SIM_SYSTEM_PLUGIN_PATH=\$HOME/ardupilot_gazebo/build:\$GZ_SIM_SYSTEM_PLUGIN_PATH" >> ~/.bashrc
  echo "export GZ_SIM_RESOURCE_PATH=\$HOME/SITL_Models/Gazebo/models:\$HOME/SITL_Models/Gazebo/worlds:\$GZ_SIM_RESOURCE_PATH" >> ~/.bashrc
fi

echo "BUILD_TAMAM"
