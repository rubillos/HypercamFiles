#!/bin/sh
# launcher.sh
# navigate to home directory, then to this directory, then execute python script, then back home

cd /
cd /home/pi/installs/mjpg-streamer/mjpg-streamer-experimental
sudo ./mjpg_streamer -o "output_http.so -w ./www" -i "input_raspicam.so -x 1296 -y 972 -fps 15 -quality 95 -awb cloudshade -ev -1 -mm matrix"
cd /
