#!/bin/sh

cd /home/pi/installs/mjpg-streamer/mjpg-streamer-experimental
sudo ./mjpg_streamer -o "output_http.so -w ./www" -i "input_raspicam.so -x 972 -y 1296 -fps 15 -quality 95 -awb tungsten -ev -1 -mm matrix -rot 90"
