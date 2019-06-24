#!/bin/sh
# launcher.sh
# navigate to home directory, then to this directory, then execute python script, then back home

cd /
cd /home/pi/Duet-timelapse
sudo python3 timelapse.py '/home/pi/timelapse-movies'
cd /
