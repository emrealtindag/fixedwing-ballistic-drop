#!/bin/bash
mkdir -p ~/.gazebo/models
cd ~/.gazebo/models
if [ ! -d "zephyr_with_ardupilot" ]; then
    git clone https://github.com/osrf/gazebo_models.git /tmp/gazebo_models
    cp -r /tmp/gazebo_models/zephyr_with_ardupilot ~/.gazebo/models/
    cp -r /tmp/gazebo_models/zephyr ~/.gazebo/models/
fi
ls ~/.gazebo/models/zephyr_with_ardupilot
