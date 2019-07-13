# Timelapse videos with your DuetWifi / Duet Ethernet / Duet 2 Maestro 3D printer!

## Requirements

  * DuetWifi or Duet Ethernet or Duet 2 Maestro controlled printer
    - RepRapFirmware v1.21 or v2.0 or higher
    - with enabled WiFi or Ethernet protocol (ethernet preferred)
  * Raspberry Pi / Single-Board Computer on the same network as your Duet
  * Webcam that returns snapshot pictures (still image) via an URL
    - Install mjpg-streamer or similiar: `http://127.0.0.1:8080/?action=snapshot`
    - Instructions are on Github at https://github.com/jacksonliam/mjpg-streamer
      - I installed into the folder /home/pi/installs
      - Enter the path to mjpg-streamer into launch-streamer.sh
  * Install these modules
      - sudo pip install requests
      - sudo pip install twilio
      - sudo pip install Pillow
      - sudo apt-get install ffmpeg
      - sudo pip install ffmpeg
  * Add this line to the end of "crontab -e"
      @reboot python /home/pi/Duet-printmonitor/timelapse.py

## Usage
```
Take snapshot pictures of your DuetWifi/DuetEthernet printer on each layer change.
Snapshots are taken during a print. On completion ffmpeg is used to make a movie. The snapshots are then deleted.
Sends an SMS via Twilio and an email with the final snapshot of the print.
Controls an LED connected to a GPIO pin to indicate status:
  On when a print is taking place
  Blinks off when an image is saved
  Flashes slowly during movie encoding
  Flashes quickly for 15 seconds if an error occurs

Rename the file settings-example.py to settings.py
Modify the lines in the file settings.py to set Duet ip address, destination folder, etc.
This script connects via Telnet to your printer

Usage: python /home/pi/Duet-printmonitor/timelapse.py
