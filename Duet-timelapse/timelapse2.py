#!/usr/bin/env python3

import datetime
import json
import os
import requests
import socket
import sys
import textwrap
import time
import traceback
import urllib3
import shutil

urllib3.disable_warnings()

# ./timelapse.py images duet http://hypercube-camera.local:8080?action=snapshot --no-verify

def log_print(*msg, file=sys.stdout):
    print(datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'), *msg, file=file)


class SimpleLineProtocol:
    def __init__(self, sock):
        self.socket = sock
        self.buffer = b''

    def write(self, msg):
        msg = msg.strip()
        msg += '\n'
        self.socket.sendall(msg.encode())

    def read_line(self):
        while b'\n' not in self.buffer:
            d = self.socket.recv(1024)
            if not d:
                raise socket.error()
            self.buffer = self.buffer + d

        i = self.buffer.find(b'\n')
        line = self.buffer[:i]
        self.buffer = self.buffer[i:].lstrip()
        return line

    def read_json_line(self):
        raw_lines = []
        line = b''
        while b'{' not in line and b'}' not in line:
            line = self.read_line()
            raw_lines.append(line)
        json_data = json.loads(line[line.find(b'{'):].decode())
        return json_data, raw_lines


def layer_changed(timelapse_folder, webcam_url, webcam_http_auth, webcam_https_verify):
    r = requests.get(webcam_url, auth=webcam_http_auth, verify=webcam_https_verify, timeout=5, stream=True)
    if r.status_code == 200:
        now = datetime.datetime.now()
        pic = os.path.join(timelapse_folder, now.strftime("%Y%m%dT%H%M%S") + ".jpg")
        with open(pic, 'wb') as f:
            for chunk in r:
                f.write(chunk)
            f.close();
        log_print("Picture taken!", pic)
    else:
        log_print('Failed to get timelapse snapshot.', file=sys.stderr)


def firmware_monitor(snapshot_folder, duet_host, webcam_url, webcam_http_auth, webcam_https_verify):
    # time.sleep(30)  # give devices time to boot and join the network

    image_count = 0

    timelapse_folder = None

    gcode_filename = 'gcode-filename.gcode'
    current_log_print = "{}-{}".format(datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S"), os.path.splitext(gcode_filename)[0])
    timelapse_folder = os.path.expanduser(snapshot_folder)
    timelapse_folder = os.path.abspath(os.path.join(timelapse_folder, current_log_print))
    os.makedirs(timelapse_folder, exist_ok=True)
    log_print("New timelapse folder created: {}{}".format(timelapse_folder, os.path.sep))

    while (image_count < 10):
        layer_changed(timelapse_folder, webcam_url, webcam_http_auth, webcam_https_verify)
        image_count = image_count + 1
        time.sleep(1)

    result = 0

    if (image_count > 8):
        log_print("\nCreating video...\n")
        #result = os.system('avconv -framerate 30 -i ' + dir + '/image%05d.jpg -vf format=yuv420p -b:v 5000k ' + 'movies/' + dateStr + '.mp4')
        now = datetime.datetime.now()
        outname = snapshot_folder + "/timelapse-" + now.strftime("%Y%m%dT%H%M%S") + ".mp4"
        result = os.system('ffmpeg -framerate 30 -y -pattern_type glob -i \'' + timelapse_folder + '/*.jpg\' -c:v libx264 -vf format=yuv420p -b:v 5000k ' + outname)

    if (result == 0):
        shutil.rmtree(timelapse_folder);



################################################################################

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print(textwrap.dedent("""
            Take snapshot pictures of your DuetWifi/DuetEthernet log_printer on every layer change.
            A new subfolder will be created with a timestamp and g-code filename for every new log_print.

            This script connects via Telnet to your log_printer, make sure to enable it in your config.g:
                M586 P2 S1 ; enable Telnet

            You need to inject the following G-Code before a new layer starts:
                M400 ; wait for all movement to complete
                M118 P4 S"LAYER CHANGE" ; take a picture
                G4 P500 ; wait a bit

            If you are using Cura, you can use the TimelapseLayerChange.py script with the Cura Post-Processing plugin.
            If you are using Simplify3D, you can enter the above commands in the "Layer Change Script" section of your process.
            Slicer-generated z-hops might cause erronously taken pictures, use firmware-retraction with z-hop instead.

            After the print is done, use ffmpeg to render a timelapse movie:
                $ ffmpeg -r 20 -y -pattern_type glob -i '*.jpg' -c:v libx264 output.mp4

            Usage: ./timelapse.py <folder> <duet_host> <webcam_url> [<auth>] [--no-verify]

                folder       - folder where all pictures will be collected, e.g., ~/timelapse_pictures
                duet_host    - DuetWifi/DuetEthernet hostname or IP address, e.g., mylog_printer.local or 192.168.1.42
                webcam_url   - HTTP or HTTPS URL that returns a JPG picture, e.g., http://127.0.0.1:8080/?action=snapshot
                auth         - optional, HTTP Basic Auth if you configured a reverse proxy with auth credentials, e.g., john:passw0rd
                --no-verify  - optional, disables HTTPS certificat verification
              """).lstrip().rstrip(), file=sys.stderr)
        sys.exit(1)

    snapshot_folder = sys.argv[1]
    duet_host = sys.argv[2]
    webcam_url = sys.argv[3]

    webcam_http_auth = None
    #if len(sys.argv) >= 5:
    #    webcam_http_auth = requests.HTTPBasicAuth(sys.argv[4].split(':'))

    webcam_https_verify = True
    for arg in sys.argv:
        if arg == '--no-verify':
            webcam_https_verify = False

    firmware_monitor(
        snapshot_folder=snapshot_folder,
        duet_host=duet_host,
        webcam_url=webcam_url,
        webcam_http_auth=webcam_http_auth,
        webcam_https_verify=webcam_https_verify
    )
