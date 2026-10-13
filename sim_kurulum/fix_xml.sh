#!/bin/bash
WORLDS_DIR=$HOME/SITL_Models/Gazebo/worlds
cat $WORLDS_DIR/vtail_runway.sdf > $WORLDS_DIR/teknofest_world.sdf

sed -i 's/model:\/\/mini_talon_vtail/model:\/\/mini_talon_vtail_cam/g' $WORLDS_DIR/teknofest_world.sdf

# Add sensors plugin safely right before <scene>
sed -i '/<scene>/i \
    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">\
      <render_engine>ogre2</render_engine>\
    </plugin>\
' $WORLDS_DIR/teknofest_world.sdf

# Strip last two tags
sed -i '/<\/world>/d' $WORLDS_DIR/teknofest_world.sdf
sed -i '/<\/sdf>/d' $WORLDS_DIR/teknofest_world.sdf

# Append targets and close tags
cat /tmp/targets_snippet.sdf >> $WORLDS_DIR/teknofest_world.sdf
echo "</world>" >> $WORLDS_DIR/teknofest_world.sdf
echo "</sdf>" >> $WORLDS_DIR/teknofest_world.sdf
