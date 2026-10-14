#!/bin/bash
# ADIM 1b - Temizlik (root olarak calisir: wsl -u root)
H=/home/emre
pkill -9 -f gzserver; pkill -9 -f gzclient; pkill -9 -f arduplane; pkill -9 -f mavproxy; pkill -9 -f sim_vehicle
echo "== Dosyalar siliniyor =="
rm -rf $H/ardupilot $H/ardupilot_gazebo $H/.gazebo $H/.ignition $H/.gz
rm -f  $H/eeprom.bin $H/mav.parm $H/mav.tlog $H/mav.tlog.raw $H/arducopter_crash.log
rm -f  $H/dumpcore.sh_* $H/dumpstack.sh_*
rm -f  $H/fix_all.py $H/fix_techpod.py $H/run_sim.sh $H/run_drone.sh $H/run_bridge.sh
rm -rf $H/logs $H/terrain
rm -rf $H/aerointel_ws/build/aerointel_simulation $H/aerointel_ws/install/aerointel_simulation

echo "== .bashrc temizleniyor =="
# eski gazebo/ardupilot/alias satirlarini kaldir
sed -i -E '/alias .*(run_plane|sabit_kanatli_iha_kodlari)/d; /gazebo\/setup\.sh/d; /GAZEBO_(MODEL|RESOURCE|PLUGIN)_PATH/d; /ardupilot_gazebo/d; /ardupilot\/Tools\/autotest/d; /SITL_Models/d; /GZ_SIM_/d; /GZ_VERSION/d' $H/.bashrc

echo "== Gazebo Classic apt paketleri kaldiriliyor =="
export DEBIAN_FRONTEND=noninteractive
apt-get remove -y --purge 'gazebo' 'gazebo-common' 'gazebo-plugin-base' 'libgazebo-dev' 'libgazebo11*' 'ros-humble-gazebo-*' 2>&1 | tail -5
apt-get autoremove -y 2>&1 | tail -3
echo TEMIZLIK_TAMAM
