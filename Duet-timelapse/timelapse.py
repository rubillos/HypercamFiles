#!/usr/bin/env python

import datetime
import json
import os
import requests
import sys
import textwrap
import time
import traceback
import json,urllib
import time
import shutil
import RPi.GPIO as GPIO

from twilio.rest import Client

import smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formatdate
from email import encoders

import PIL.Image as Image

led_pin = 23
printer_status_delay = 5.0

#@reboot sh /home/pi/Duet-timelapse/launch-streamer.sh
#@reboot sh /home/pi/Duet-timelapse/launch-timelapse.sh
# ./mjpg_streamer -o "output_http.so -w ./www" -i "input_raspicam.so -x 1296 -y 972 -fps 15"

# sudo pip install requests
# sudo pip install twilio
# sudo pip install Pillow
# sudo apt-get install ffmpeg
# sudo pip install ffmpeg
#
# transform: rotate(45deg);
#
# ffmpeg -framerate 30 -y -pattern_type glob -i 'home/pi/timelapse-movies/images/benchy/*.jpg' -c:v h264_omx -vf format=yuv420p -vf "transpose=1" -b:v 10000k outmovie1.mp4

twilio_account_sid = "***REMOVED***"
twilio_auth_token  = "***REMOVED***"
twilio_to_number = "***REMOVED***"
twilio_from_number = "***REMOVED***"

client = Client(twilio_account_sid, twilio_auth_token)

smtp_port = 465  # For SSL
smtp_server = "***REMOVED***"
printer_name = "Hypercube"
sender_email = "***REMOVED***"
sender_from = "Hypercam <***REMOVED***>"
sender_password = "***REMOVED***"
receiver_email = '"Randy Ubillos"<randy@mac.com>'
sender_to = "Randy Ubillos"

def log_print(*msg):
    print(msg)
    # print(datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'), *msg, sys.stderr)

def layer_changed(timelapse_folder, webcam_url):
    r = requests.get(webcam_url)
    if r.status_code == 200:
        now = datetime.datetime.now()
        picPath = os.path.join(timelapse_folder, now.strftime("%Y%m%dT%H%M%S") + ".jpg")
        with open(picPath, 'wb') as f:
            for chunk in r:
                f.write(chunk)

        set_active_light(False);
        time.sleep(0.25)
        set_active_light(True);

        log_print("Picture taken and saved to disk.")
        return picPath
    else:
        log_print('Failed to get timelapse snapshot.')
        return ""

def set_active_light(enabled):
    if enabled:
        GPIO.output(led_pin, GPIO.HIGH)
    else:
        GPIO.output(led_pin, GPIO.LOW)

def blink_error(waitTime):
    p = GPIO.PWM(led_pin, 0.2)
    p.start(50)
    time.sleep(waitTime)
    p.stop()
    set_active_light(False)

def send_email(subject, msgText, picPath):
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = sender_from
    msg['To'] = receiver_email

    msg.attach(MIMEText(msgText))

    picture= Image.open(picPath)
    picture.rotate(270, expand=1).save(picPath)

    part = MIMEBase('application', "octet-stream")
    part.set_payload(open(picPath, "rb").read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', 'attachment; filename="lastimage.jpg"')   # File name and format name
    msg.attach(part)

    sslcontext = ssl.create_default_context()
    server = smtplib.SMTP_SSL(smtp_server, smtp_port, sslcontext)
    server.login(sender_email, sender_password)
    server.sendmail(sender_email, receiver_email, msg.as_string())
    server.quit()

def send_sms(msgBody):
    message = client.messages.create(from_=twilio_from_number, to=twilio_to_number, body=msgBody)
    #print(message.sid)

def firmware_monitor(snapshot_folder, duet_host, webcam_url):
    # time.sleep(30)  # give devices time to boot and join the network

    while True:
        try:
            timelapse_folder = None
            lastZ = -1
            image_count = 0
            gcode_filename = ''
            startTime = time.time()
            last_picture_path = ""

            while True:
                data = json.loads(urllib.urlopen(duet_host + "/rr_status?type=3").read().decode("utf-8"))
                status = data['status']
                currentZ = data['coords']['xyz'][2]

                # log_print(data);

                # runTime = time.time() - startTime
                # if runTime > 5 and runTime < 40:
                #     status = 'P'

                if status == 'P' and not timelapse_folder:
                    fileInfo = json.loads(urllib.urlopen(duet_host + "/rr_fileinfo").read().decode("utf-8"))
                    fileName = fileInfo['fileName']
                    # fileName = 'SampleName'
                    startTime = time.time()

                    gcode_filename = os.path.splitext(os.path.basename(fileName))[0]
                    current_log_print = "images/{}-{}".format(datetime.datetime.now().strftime("%Y-%m-%d-%h-%m-%s"), gcode_filename)
                    timelapse_folder = os.path.expanduser(snapshot_folder)
                    timelapse_folder = os.path.abspath(os.path.join(timelapse_folder, current_log_print))
                    os.makedirs(timelapse_folder)
                    set_active_light(True);
                    log_print("New timelapse folder created: {}{}".format(timelapse_folder, os.path.sep))
                    log_print("Waiting for layer changes...")

                if status == 'I' and timelapse_folder:
                    result = 0

                    if (image_count > 5):
                        log_print("\nCreating video...\n")
                        now = datetime.datetime.now()
                        p = GPIO.PWM(led_pin, 4.0)
                        p.start(20)
                        outname = snapshot_folder + "/" + gcode_filename + "-" + now.strftime("%Y%m%dT%H%M%S") + ".mp4"
                        result = os.system('ffmpeg -framerate 30 -y -pattern_type glob -i \'' + timelapse_folder + '/*.jpg\' -c:v h264_omx -vf format=yuv420p -vf "transpose=1" -b:v 10000k ' + outname)

                        if result == 0:
                            log_print("\nSuccess! New movie is " + outname + "\n")

                            printTime = time.time() - startTime
                            msgBody = printer_name + " job complete: " + gcode_filename + "\nTotal print time: " + str(datetime.timedelta(seconds = printTime)) + "\n\n"
                            send_sms(msgBody)
                            send_email(printer_name, msgBody, last_picture_path)
                            log_print(msgBody)
                            shutil.rmtree(timelapse_folder);

                        p.stop()

                    else:
                        log_print("\nMovie too short - canceling\n")
                        shutil.rmtree(timelapse_folder);

                    timelapse_folder = None
                    lastZ = -1
                    last_picture_path = ''
                    image_count = 0
                    log_print("Print finished.")

                if status == 'I':
                    set_active_light(False);

                if timelapse_folder:
                    if currentZ != lastZ:
                        last_picture_path = layer_changed(timelapse_folder, webcam_url)
                        image_count = image_count+1

                # lastZ = currentZ - 1
                lastZ = currentZ
                time.sleep(printer_status_delay)

        except Exception as e:
            # log_print('ERROR', e)
            traceback.print_exc()

        log_print("Sleeping for a bit...")
        blink_error(15)


################################################################################

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print(textwrap.dedent("""
            Take snapshot pictures of your DuetWifi/DuetEthernet log_printer on every layer change.
            A new subfolder will be created with a timestamp and g-code filename for every new log_print.

            This script connects via HTTP to get printer status
            It watches the z axis to see when layers change
            On completion it creates a movie and deletes the still images

            Usage: ./timelapse.py <folder> <duet_host> <webcam_url>

                folder       - folder where all pictures will be collected, e.g., ~/timelapse_pictures
                duet_host    - DuetWifi/DuetEthernet hostname or IP address, e.g., mylog_printer.local or 192.168.1.42
                webcam_url   - HTTP or HTTPS URL that returns a JPG picture, e.g., http://127.0.0.1:8080/?action=snapshot
              """).lstrip().rstrip())
        sys.exit(1)

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(led_pin, GPIO.OUT)
    set_active_light(False)

    snapshot_folder = sys.argv[1]
    duet_host = sys.argv[2]
    webcam_url = sys.argv[3]

    log_print('Start Timelapse System')

    firmware_monitor(
        snapshot_folder,
        duet_host,
        webcam_url
    )
