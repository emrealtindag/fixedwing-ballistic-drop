#!/bin/bash
set -e

echo "== Baslatici Scriptler Olusturuluyor =="

cat << 'EOF' > ~/run_sim.sh
#!/bin/bash
# 1. Gazebo Harmonic'i ve Teknofest Dunyasini Baslatir
source ~/.bashrc
echo "Gazebo Harmonic Baslatiliyor..."
gz sim -v4 -r $HOME/SITL_Models/Gazebo/worlds/teknofest_world.sdf
EOF

cat << 'EOF' > ~/run_drone.sh
#!/bin/bash
# 2. ArduPilot'u Mini Talon V-Tail ayarlariyla baslatir
source ~/.bashrc
killall -9 arducopter mavproxy.py sim_vehicle.py arduplane 2>/dev/null

echo "ArduPilot SITL Baslatiliyor..."
sim_vehicle.py -v ArduPlane -f JSON --model JSON --add-param-file=$HOME/SITL_Models/Gazebo/config/mini_talon_vtail.param --console
EOF

cat << 'EOF' > ~/run_bridge.sh
#!/bin/bash
# 3. ROS 2 Goruntu Koprusunu Baslatir
source /opt/ros/humble/setup.bash
echo "ROS 2 <-> Gazebo Goruntu Koprusu Baslatiliyor..."
ros2 run ros_gz_bridge parameter_bridge /camera_down/image_raw@sensor_msgs/msg/Image@gz.msgs.Image
EOF

chmod +x ~/run_sim.sh ~/run_drone.sh ~/run_bridge.sh
echo "SCRIPTLER_TAMAM"
