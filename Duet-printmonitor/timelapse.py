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

from subprocess import Popen, PIPE
from twilio.rest import Client

import smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formatdate
from email import encoders

import PIL.Image as Image

from settings import *

client = Client(twilio_account_sid, twilio_auth_token)

def log_print(*msg):
    print(msg)
    # print(datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'), *msg, sys.stderr)

def layer_changed(timelapse_folder, webcam_url):
    r = requests.get(webcam_url)
    if r.status_code == 200:
        now = datetime.datetime.now()
        set_active_light(False);
        time.sleep(0.25)
        set_active_light(True);
        picPath = os.path.join(timelapse_folder, now.strftime("%Y%m%dT%H%M%S") + ".jpg")
        with open(picPath, 'wb') as f:
            for chunk in r:
                f.write(chunk)

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
    p = GPIO.PWM(led_pin, 20)
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
    client.messages.create(from_=twilio_from_number, to=twilio_to_number, body=msgBody)

def firmware_monitor():
    while True:
        try:
            timelapse_folder = None
            lastLayer = -1
            image_count = 0
            gcode_filename = ''
            startTime = time.time()
            last_picture_path = ""

            while True:
                data = json.loads(urllib.urlopen(duet_host + "/rr_status?type=3").read().decode("utf-8"))
                status = data['status']
                currentLayer = data['currentLayer']

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

                    if (image_count > minimum_image_count):
                        log_print("\nCreating video...\n")
                        now = datetime.datetime.now()
                        p = GPIO.PWM(led_pin, 4.0)
                        p.start(20)
                        outname = snapshot_folder + "/" + gcode_filename + "-" + now.strftime("%Y%m%dT%H%M%S") + ".mp4"
                        result = os.system('ffmpeg -y -pattern_type glob -i \'' + timelapse_folder + '/*.jpg\' ' + encoding_options + ' ' + outname)

                        if result == 0:
                            log_print("\nSuccess! New movie is " + outname + "\n")

                            printTime = long(time.time() - startTime)
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
                    lastLayer = -1
                    last_picture_path = ''
                    image_count = 0
                    log_print("Print finished.")

                if status == 'I':
                    set_active_light(False);

                if timelapse_folder:
                    if currentLayer > lastLayer:
                        last_picture_path = layer_changed(timelapse_folder, webcam_url)
                        image_count = image_count+1

                # lastLayer = currentLayer - 1
                lastLayer = currentLayer
                time.sleep(printer_status_delay)

        except Exception as e:
            # log_print('ERROR', e)
            traceback.print_exc()

        log_print("Sleeping for a bit...")
        blink_error(15)


################################################################################

if __name__ == "__main__":
    streamer = None;

    try:
        log_print('Start Timelapse System')
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(led_pin, GPIO.OUT)
        set_active_light(False)
        streamer = Popen('sh launch-streamer.sh', shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        firmware_monitor()

    except KeyboardInterrupt:
        pass
    finally:
        streamer.kill()
