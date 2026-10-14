#!/bin/bash
set -e

MODELS_DIR=$HOME/SITL_Models/Gazebo/models
WORLDS_DIR=$HOME/SITL_Models/Gazebo/worlds

echo "== Mini Talon V-Tail Kopyalaniyor ve Kamera Ekleniyor =="
# Orijinal modeli bozmadan kopyasini alalim
rm -rf $MODELS_DIR/mini_talon_vtail_cam
cp -r $MODELS_DIR/mini_talon_vtail $MODELS_DIR/mini_talon_vtail_cam
sed -i 's/<model name="mini_talon_vtail">/<model name="mini_talon_vtail_cam">/g' $MODELS_DIR/mini_talon_vtail_cam/model.sdf

cat << 'EOF' > /tmp/camera_snippet.sdf
    <link name="camera_link">
      <pose>0.1 0 -0.1 0 1.57079632679 0</pose> <!-- Tam asagi bakacak sekilde 90 derece donduruldu -->
      <inertial>
        <mass>0.05</mass>
        <inertia>
          <ixx>0.00001</ixx><iyy>0.00001</iyy><izz>0.00001</izz>
        </inertia>
      </inertial>
      <sensor name="camera_down" type="camera">
        <camera>
          <horizontal_fov>1.047</horizontal_fov>
          <image>
            <width>640</width>
            <height>480</height>
            <format>R8G8B8</format>
          </image>
          <clip><near>0.1</near><far>1000</far></clip>
        </camera>
        <always_on>1</always_on>
        <update_rate>30</update_rate>
        <visualize>true</visualize>
        <topic>camera_down/image_raw</topic>
      </sensor>
    </link>
    <joint name="camera_joint" type="fixed">
      <parent>base_link</parent>
      <child>camera_link</child>
    </joint>
EOF

# Snippet'i modelin en sonuna (</model> etiketinden hemen onceye) ekle
sed -i '/<\/model>/e cat /tmp/camera_snippet.sdf' $MODELS_DIR/mini_talon_vtail_cam/model.sdf
sed -i 's/<name>Mini Talon V-tail<\/name>/<name>Mini Talon V-tail Cam<\/name>/g' $MODELS_DIR/mini_talon_vtail_cam/model.config

echo "== Teknofest Dunyasi Olusturuluyor (Hedeflerle birlikte) =="
cat $WORLDS_DIR/vtail_runway.sdf > $WORLDS_DIR/teknofest_world.sdf

# Yeni modelimizi cagiracak sekilde guncelle
sed -i 's/model:\/\/mini_talon_vtail/model:\/\/mini_talon_vtail_cam/g' $WORLDS_DIR/teknofest_world.sdf

# Kameranin calismasi icin Sensors eklentisi sart
sed -i '/<plugin filename="gz-sim-navsat-system"/a \    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors"><render_engine>ogre2</render_engine></plugin>' $WORLDS_DIR/teknofest_world.sdf

cat << 'EOF' > /tmp/targets_snippet.sdf
    <!-- Kirmizi Hedef (Red Target) -->
    <model name="red_target">
      <static>true</static>
      <pose>80 0 0.1 0 0 0</pose>
      <link name="link">
        <visual name="visual">
          <geometry><box><size>2 2 0.01</size></box></geometry>
          <material><ambient>1 0 0 1</ambient><diffuse>1 0 0 1</diffuse></material>
        </visual>
      </link>
    </model>
    
    <!-- Mavi Hedef (Blue Target) -->
    <model name="blue_target">
      <static>true</static>
      <pose>140 0 0.1 0 0 0</pose>
      <link name="link">
        <visual name="visual">
          <geometry><box><size>2 2 0.01</size></box></geometry>
          <material><ambient>0 0 1 1</ambient><diffuse>0 0 1 1</diffuse></material>
        </visual>
      </link>
    </model>
EOF

sed -i '/<\/world>/e cat /tmp/targets_snippet.sdf' $WORLDS_DIR/teknofest_world.sdf

echo "KAMERA_TAMAM"
