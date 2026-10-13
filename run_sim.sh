#!/bin/bash
export PATH=$PATH:$HOME/ardupilot/Tools/autotest
export GAZEBO_MODEL_PATH=$HOME/ardupilot_gazebo/models
export GAZEBO_RESOURCE_PATH=$HOME/ardupilot_gazebo/worlds:$GAZEBO_RESOURCE_PATH
export GAZEBO_PLUGIN_PATH=$HOME/ardupilot_gazebo/build:$GAZEBO_PLUGIN_PATH

echo "Baslatiliyor..."
gazebo --verbose $HOME/ardupilot_gazebo/worlds/iris_arducopter_runway.world
