#!/usr/bin/env python3

import datetime
import json
import os
import requests
import sys
import textwrap
import time
import traceback
import urllib3
import json,urllib.request
import time
import shutil
import RPi.GPIO as GPIO

urllib3.disable_warnings()


def log_print(*msg, file=sys.stdout):
    # print(msg)
    print(datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'), *msg, file=file)


def layer_changed(timelapse_folder, webcam_url, webcam_http_auth, webcam_https_verify):
    r = requests.get(webcam_url, auth=webcam_http_auth, verify=webcam_https_verify, timeout=5, stream=True)
    if r.status_code == 200:
        now = datetime.datetime.now()
        pic = os.path.join(timelapse_folder, now.strftime("%Y%m%dT%H%M%S") + ".jpg")
        with open(pic, 'wb') as f:
            for chunk in r:
                f.write(chunk)
        log_print("Picture taken!", pic)
    else:
        log_print('Failed to get timelapse snapshot.', file=sys.stderr)

def set_active_light(enabled):
    if enabled:
        GPIO.output(17, GPIO.HIGH)
    else:
        GPIO.output(17, GPIO.LOW)

def firmware_monitor(snapshot_folder, duet_host, webcam_url, webcam_http_auth, webcam_https_verify):
    # time.sleep(30)  # give devices time to boot and join the network

    while True:
        try:
            timelapse_folder = None
            lastLayer = -1
            image_count = 0
            fileName = ''
            startTime = time.time()

            while True:
                data = json.loads(urllib.request.urlopen(duet_host + "/rr_status?type=3").read().decode("utf-8"))
                status = data['status']
                currentLayer = data['currentLayer'];

                log_print(data);

                runTime = time.time() - startTime;
                if runTime > 5 and runTime < 40:
                    status = 'P'

                if status == 'P' and not timelapse_folder:
                    # fileInfo = json.loads(urllib.request.urlopen(duet_host + "/rr_fileinfo").read().decode("utf-8"))
                    # fileName = fileInfo['fileName']
                    fileName = 'SampleName'

                    # log_print("Print started:", fileInfo)
                    gcode_filename = os.path.basename(fileName)
                    current_log_print = "images/{}-{}".format(datetime.datetime.now().strftime("%Y-%m-%d"),
                                                       os.path.splitext(gcode_filename)[0])
                    timelapse_folder = os.path.expanduser(snapshot_folder)
                    timelapse_folder = os.path.abspath(os.path.join(timelapse_folder, current_log_print))
                    os.makedirs(timelapse_folder, exist_ok=True)
                    set_active_light(True);
                    log_print("New timelapse folder created: {}{}".format(timelapse_folder, os.path.sep))
                    log_print("Waiting for layer changes...")

                if status == 'I' and timelapse_folder:
                    result = 0

                    if (image_count > 5):
                        log_print("\nCreating video...\n")
                        #result = os.system('avconv -framerate 30 -i ' + dir + '/image%05d.jpg -vf format=yuv420p -b:v 5000k ' + 'movies/' + dateStr + '.mp4')
                        now = datetime.datetime.now()
                        outname = snapshot_folder + "/" + fileName + "-" + now.strftime("%Y%m%dT%H%M%S") + ".mp4"
                        result = os.system('ffmpeg -framerate 30 -y -pattern_type glob -i \'' + timelapse_folder + '/*.jpg\' -c:v libx264 -vf format=yuv420p -b:v 5000k ' + outname)

                        if result == 0:
                            log_print("\nSuccess! New movie is " + outname + "\n")
                            shutil.rmtree(timelapse_folder);
                    else:
                        log_print("\nMovie too short - canceling\n")
                        shutil.rmtree(timelapse_folder);

                    timelapse_folder = None
                    fileName = ''
                    lastLayer = -1
                    image_count = 0
                    log_print("Print finished.")

                if status == 'I':
                    set_active_light(False);

                if timelapse_folder:
                    if currentLayer != lastLayer:
                        layer_changed(timelapse_folder, webcam_url, webcam_http_auth, webcam_https_verify)
                        image_count = image_count+1

                # lastLayer = currentLayer
                lastLayer = currentLayer - 1
                time.sleep(5)

        except Exception as e:
            log_print('ERROR', e, file=sys.stderr)
            traceback.print_exc()
        log_print("Sleeping for a bit...", file=sys.stderr)
        time.sleep(15)


################################################################################

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print(textwrap.dedent("""
            Take snapshot pictures of your DuetWifi/DuetEthernet log_printer on every layer change.
            A new subfolder will be created with a timestamp and g-code filename for every new log_print.

            This script connects via HTTP to get printer status
            It watches the currentLayer to see when layers change
            On completion it creates a movie and deletes the still images

            Usage: ./timelapse.py <folder> <duet_host> <webcam_url> [<auth>] [--no-verify]

                folder       - folder where all pictures will be collected, e.g., ~/timelapse_pictures
                duet_host    - DuetWifi/DuetEthernet hostname or IP address, e.g., mylog_printer.local or 192.168.1.42
                webcam_url   - HTTP or HTTPS URL that returns a JPG picture, e.g., http://127.0.0.1:8080/?action=snapshot
                auth         - optional, HTTP Basic Auth if you configured a reverse proxy with auth credentials, e.g., john:passw0rd
                --no-verify  - optional, disables HTTPS certificat verification
              """).lstrip().rstrip(), file=sys.stderr)
        sys.exit(1)

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(17, GPIO.OUT)

    snapshot_folder = sys.argv[1]
    duet_host = sys.argv[2]
    webcam_url = sys.argv[3]

    webcam_http_auth = None
    if len(sys.argv) >= 5:
        webcam_http_auth = requests.HTTPBasicAuth(sys.argv[4].split(':'))

    webcam_https_verify = True
    for arg in sys.argv:
        if arg == '--no-verify':
            webcam_https_verify = False

    log_print('Start Timelapse System')

    firmware_monitor(
        snapshot_folder=snapshot_folder,
        duet_host=duet_host,
        webcam_url=webcam_url,
        webcam_http_auth=webcam_http_auth,
        webcam_https_verify=webcam_https_verify
    )
