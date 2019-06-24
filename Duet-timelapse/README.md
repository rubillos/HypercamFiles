# Timelapse videos with your DuetWifi / Duet Ethernet / Duet 2 Maestro 3D printer!

## Requirements

  * DuetWifi or Duet Ethernet or Duet 2 Maestro controlled printer
    - RepRapFirmware v1.21 or v2.0 or higher
    - with enabled WiFi or Ethernet protocol
    - with enabled Telnet protocol
  * Raspberry Pi / Single-Board Computer on the same network as your Duet
    - with Python 3 and the `requests` package
  * Webcam that returns snapshot pictures (still image) via an URL
    - mjpg-streamer or similiar: `http://127.0.0.1:8080/?action=snapshot`

## Usage
```
Take snapshot pictures of your DuetWifi/DuetEthernet log_printer on every layer change.
A new subfolder will be created with a timestamp and g-code filename for every new log_print.

This script connects via HTTP to your log_printer

Generates a movie from still images using ffmpeg when a print is complete

Usage: ./timelapse.py <folder> <duet_host> <webcam_url> [<auth>] [--no-verify]

    folder       - folder where all pictures will be collected, e.g., ~/timelapse_pictures
    duet_host    - DuetWifi/DuetEthernet hostname or IP address, e.g., mylog_printer.local or 192.168.1.42
    webcam_url   - HTTP or HTTPS URL that returns a JPG picture, e.g., http://127.0.0.1:8080/?action=snapshot
    auth         - HTTP Basic Auth if you configured a reverse proxy with auth credentials, e.g., john:passw0rd
    --no-verify  - Disables HTTPS certificat verification
```
