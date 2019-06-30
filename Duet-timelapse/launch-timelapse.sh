#!/bin/sh
# launcher.sh
# navigate to home directory, then to this directory, then execute python script, then back home

cd /
cd /home/pi/Duet-timelapse
sudo python timelapse.py '/home/pi/timelapse-movies' 'http://192.168.7.250' 'http://127.0.0.1:8080/?action=snapshot'
cd /
