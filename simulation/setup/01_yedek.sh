#!/bin/bash
# ADIM 1a - Yedek (kullanici olarak calisir)
set -e
cd ~
TS=$(date +%Y%m%d_%H%M)
B=~/ESKI_YEDEK_$TS
mkdir -p $B
echo "Yedek klasoru: $B"

# ardupilot: sadece bizim degisikliklerimiz (repo yeniden indirilecek)
if [ -d ~/ardupilot ]; then
  (cd ~/ardupilot && git diff > $B/ardupilot_degisiklikler.diff; git status --short > $B/ardupilot_status.txt; git log -1 --oneline > $B/ardupilot_commit.txt) || true
fi

# kucuk dosyalar
tar czf $B/home_dosyalari.tar.gz --ignore-failed-read \
  eeprom.bin mav.parm mav.tlog mav.tlog.raw fix_all.py fix_techpod.py \
  run_sim.sh run_drone.sh run_bridge.sh arducopter_crash.log logs .bashrc 2>/dev/null || true

# eski gazebo eklentisi ve modeller (build haric)
tar czf $B/ardupilot_gazebo_eski.tar.gz --exclude=ardupilot_gazebo/build ardupilot_gazebo 2>/dev/null || true
tar czf $B/dot_gazebo.tar.gz --exclude=.gazebo/SITL_Models/.git .gazebo 2>/dev/null || true
cp ~/.bashrc $B/bashrc.bak
ls -lh $B
echo YEDEK_TAMAM
