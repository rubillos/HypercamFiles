#!/usr/bin/env python

import datetime
import json
import os
import requests
import socket
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

debugging = False

twilio_client = None
pwm_channel = None

if send_twilio_sms:
    twilio_client = Client(twilio_account_sid, twilio_auth_token)

def log_print(*msg):
    print(msg)
    # print(current_time_string(), *msg, sys.stderr)

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
        line = b''
        while b'{' not in line and b'}' not in line:
            line = self.read_line()
        json_data = json.loads(line[line.find(b'{'):].decode())
        return json_data

def current_time_string():
    return datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

def layer_changed(timelapse_folder, webcam_url):
    r = requests.get(webcam_url)
    if r.status_code == 200:
        set_active_light(False)
        time.sleep(0.25)
        set_active_light(True)
        picPath = os.path.join(timelapse_folder, current_time_string() + ".jpg")
        with open(picPath, 'wb') as f:
            for chunk in r:
                f.write(chunk)

        log_print("Picture taken and saved to disk.")
        return picPath
    else:
        log_print('Failed to get timelapse snapshot.')
        return ""

def set_active_light(enabled):
    pwm_channel = None
    if enabled:
        GPIO.output(led_pin, GPIO.HIGH)
    else:
        GPIO.output(led_pin, GPIO.LOW)

def blink_error(waitTime):
    pwm_channel = None
    pwm_channel = GPIO.PWM(led_pin, 20)
    pwm_channel.start(50)
    time.sleep(waitTime)
    pwm_channel.stop()
    pwm_channel = None
    set_active_light(False)

def send_email(subject, msgText, picPath):
    if send_email:
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
    if twilio_client:
        twilio_client.messages.create(from_=twilio_from_number, to=twilio_to_number, body=msgBody)

def make_a_movie(output_filename, source_folder, elapsed_time, last_picture_path):
    if create_movie:
        log_print("Creating video...")
        pwm_channel = None
        pwm_channel = GPIO.PWM(led_pin, 4.0)
        pwm_channel.start(20)
        outname = snapshot_folder + "/" + output_filename + "-" + current_time_string() + ".mp4"
        system_command = 'ffmpeg -y -framerate 30 -pattern_type glob -i \'' + source_folder + '/*.jpg\' ' + encoding_options + ' \'' + outname + '\''
        log_print(system_command)
        result = os.system(system_command)

        if result == 0:
            log_print("Success! New movie is " + outname)

            msgBody = printer_name + " job complete: " + output_filename + "\nTotal print time: " + str(datetime.timedelta(seconds = elapsed_time)) + "\n\n"
            send_sms(msgBody)
            send_email(printer_name, msgBody, last_picture_path)
            log_print(msgBody)
            shutil.rmtree(source_folder)

        pwm_channel.stop()
        pwm_channel = None

def firmware_monitor():
    sock = None
    conn = None

    while True:
        try:
            log_print("Connecting to {}...".format(duet_host))
            sock = socket.create_connection((duet_host, 23), timeout=10)
            time.sleep(4.5)  # RepRapFirmware uses a 4-second ignore period after connecting
            conn = SimpleLineProtocol(sock)
            log_print("Connection established.")

            timelapse_folder = None
            currentLayer = -1
            lastLayer = -1
            image_count = 0
            gcode_filename = ''
            startTime = time.time()
            last_picture_path = ""

            while True:
                status = "I"

                conn.write('M408 S4')
                data = conn.read_json_line()

                if debugging:
                    runTime = time.time() - startTime
                    if runTime > 3 and image_count <= minimum_image_count:
                        data['status'] = 'P'
                        data['currentLayer'] = data['currentLayer'] + 1

                status = data['status']
                currentLayer = data['currentLayer']

                log_print("Printer status: " + status)
                # log_print(data)

                if status == 'P' and not timelapse_folder:
                    conn.write('M36')
                    fileInfo = conn.read_json_line()

                    if debugging:
                        fileInfo['fileName'] = 'SampleName'
                    else:
                        startTime = time.time()

                    fileName = fileInfo['fileName']
                    gcode_filename = os.path.splitext(os.path.basename(fileName))[0]
                    current_print_folder = "images/{}-{}".format(current_time_string(), gcode_filename)
                    timelapse_folder = os.path.expanduser(snapshot_folder)
                    timelapse_folder = os.path.abspath(os.path.join(timelapse_folder, current_print_folder))
                    os.makedirs(timelapse_folder)
                    set_active_light(True)
                    log_print("New timelapse folder created: {}{}".format(timelapse_folder, os.path.sep))
                    log_print("Waiting for layer changes...")

                if status == 'I' and timelapse_folder:
                    if create_movie:
                        if image_count > minimum_image_count or debugging:
                            make_a_movie(gcode_filename, timelapse_folder, long(time.time() - startTime), last_picture_path)
                        else:
                            log_print("Movie too short - canceling")
                            shutil.rmtree(timelapse_folder)

                    timelapse_folder = None
                    lastLayer = -1
                    last_picture_path = ''
                    if not debugging:
                        image_count = 0
                    log_print("Print finished.")

                if status == 'I':
                    set_active_light(False)

                if timelapse_folder:
                    if currentLayer > lastLayer:
                        last_picture_path = layer_changed(timelapse_folder, webcam_url)
                        image_count = image_count+1

                if debugging:
                    lastLayer = currentLayer - 1
                    if status == 'I' or image_count > minimum_image_count:
                        time.sleep(printer_status_delay)
                else:
                    lastLayer = currentLayer
                    time.sleep(printer_status_delay)

        except Exception as e:
            # log_print('ERROR', e)
            traceback.print_exc()

        if sock:
            log_print("Exception occured. Will restart after 15 seconds...")
            blink_error(15)
            sock.close()
            sock = None
            conn = None
        else:
            log_print("Unable to connect to printer. Will try again in 5 seconds...")
            time.sleep(5)

################################################################################

if __name__ == "__main__":
    streamer = None

    try:
        log_print('Start Timelapse System')
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(led_pin, GPIO.OUT)
        set_active_light(False)

        streamer = Popen(start_mjpg_streamer, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd = mjpg_streamer_folder)

        if not debugging:
            log_print('Delay while printer starts up...')
            time.sleep(initial_wait)

        firmware_monitor()

    except Exception as e:
        traceback.print_exc()

    except KeyboardInterrupt:
        pass
    finally:
        if streamer:
            streamer.kill()
