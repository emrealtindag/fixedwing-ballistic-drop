#!/bin/bash
export PATH=$PATH:$HOME/ardupilot/Tools/autotest
# SITL'i Gazebo ile baslatmak icin -f gazebo-zephyr parametresini kullaniyoruz
# Ancak iceride ucak modeli olarak klasik kuyruklu cessna baglanacak.
sim_vehicle.py -v ArduPlane -f gazebo-zephyr --console
