#!/bin/bash
# ADIM 2 - Gazebo Harmonic + ros-humble-ros-gzharmonic (root olarak)
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y lsb-release wget gnupg curl
wget -q https://packages.osrfoundation.org/gazebo.gpg -O /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" > /etc/apt/sources.list.d/gazebo-stable.list
apt-get update
apt-get install -y gz-harmonic
# Harmonic derleme bagimliliklari (ardupilot_gazebo icin)
apt-get install -y libgz-sim8-dev rapidjson-dev libopencv-dev \
  libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev gstreamer1.0-plugins-bad gstreamer1.0-libav gstreamer1.0-gl \
  cmake build-essential git
# ROS 2 Humble <-> Gazebo Harmonic koprusu
apt-get install -y ros-humble-ros-gzharmonic || echo "UYARI: ros-humble-ros-gzharmonic kurulamadi"
gz sim --version
echo GAZEBO_TAMAM
