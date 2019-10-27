#!/usr/bin/env python

import datetime
import json
import os
import requests
import socket
import select
import sys
import textwrap
import time
import traceback
import json,urllib
import time
import shutil
import RPi.GPIO as GPIO
import pygame as pg

from subprocess import Popen, PIPE
from twilio.rest import Client

import smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formatdate
from email import encoders

import PIL.Image as Image

from enum import Enum

from settings import *

debugging = False

twilio_client = None
pwm_channel = None

sock = None
conn = None

printing = False
awaiting_baby_step = False

if send_twilio_sms:
    twilio_client = Client(twilio_account_sid, twilio_auth_token)

def log_print(*msg):
    print(msg)
    # print(current_time_string(), *msg, sys.stderr)


class InterpolatedArray(object):
  def __init__(self, points):
    self.points = sorted(points)

  def __getitem__(self, x):
    if x < self.points[0][0]:
        return self.points[0][1]
    elif x >= self.points[-1][0]:
        return self.points[-1][1]
    else:
        lower_point, upper_point = self._GetBoundingPoints(x)
        return self._Interpolate(x, lower_point, upper_point)

  def _GetBoundingPoints(self, x):
    lower_point = None
    upper_point = self.points[0]
    for point in self.points[1:]:
      lower_point = upper_point
      upper_point = point
      if x <= upper_point[0]:
        break
    return lower_point, upper_point

  def _Interpolate(self, x, lower_point, upper_point):
    slope = (float(upper_point[1] - lower_point[1]) / (upper_point[0] - lower_point[0]))
    return lower_point[1] + (slope * (x - lower_point[0]))


class SimpleLineProtocol:
    def __init__(self, sock):
        self.socket = sock
        self.buffer = b''

    def write(self, msg):
        msg = msg.strip()
        msg += '\n'
        self.socket.sendall(msg.encode())

    def read_line(self):
        line = b''
        readable, writable, exceptional = select.select([sock], [], [], 0.5)

        if len(readable) > 0:
            d = self.socket.recv(1024)
            if not d:
                raise socket.error()
            self.buffer = self.buffer + d

            if b'\n' in self.buffer:
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

    def read_data(self):
        json_data = None
        message = None

        line = self.read_line()

        if b'{' in line and b'}' in line:
            json_data = json.loads(line[line.find(b'{'):].decode())
        elif len(line) > 0:
            message = line

        return json_data,message


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

        if debugging:
            log_print("Picture taken and saved to disk.")

        return picPath
    else:
        if debugging:
            log_print('Failed to get timelapse snapshot.')

        return ""


def clear_pwm():
    global pwm_channel

    if pwm_channel != None:
        pwm_channel.stop()
        pwm_channel = None


def set_active_light(enabled):
    clear_pwm()
    if enabled:
        GPIO.output(led_pin, GPIO.HIGH)
    else:
        GPIO.output(led_pin, GPIO.LOW)


def blink_error(waitTime):
    global pwm_channel

    clear_pwm()
    pwm_channel = GPIO.PWM(led_pin, 20)
    pwm_channel.start(50)
    time.sleep(waitTime)
    clear_pwm()
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


def send_sms(msg_body):
    if twilio_client:
        twilio_client.messages.create(from_=twilio_from_number, to=twilio_to_number, body=msg_body)


def make_a_movie(output_filename, source_folder, elapsed_time, last_picture_path, current_z):
    global pwm_channel

    if create_movie:
        log_print("Creating video... (total height =" + str(current_z) + "mm)")
        crop_table = InterpolatedArray(crop_factors)
        clear_pwm()
        pwm_channel = GPIO.PWM(led_pin, 4.0)
        pwm_channel.start(20)
        outname = snapshot_folder + "/" + output_filename + "-" + current_time_string() + ".mp4"
        crop_factor = crop_table[current_z]
        crop_options = " -vf \'crop=y=0:h=in_h*" + str(crop_factor) + "\'"
        system_command = 'ffmpeg -y -framerate 30 -pattern_type glob -i \'' + source_folder + '/*.jpg\' ' + encoding_options + crop_options + ' \'' + outname + '\''
        log_print(system_command)
        result = os.system(system_command)

        if result == 0:
            log_print("Success! New movie is " + outname)

            msg_body = printer_name + " job complete: " + output_filename + "\nTotal print time: " + str(datetime.timedelta(seconds = elapsed_time)) + "\n\n"
            send_sms(msg_body)
            send_email(printer_name, msg_body, last_picture_path)
            log_print(msg_body)
            shutil.rmtree(source_folder)

        clear_pwm()


def play_sound(sound_name):
    while pg.mixer.music.get_busy():
        pass

    sound_path = sounds_folder + "/" + sound_name

    try:
        pg.mixer.music.load(sound_path)
        # print("Music file {} loaded!".format(sound_path))
    except pygame.error:
        print("File {} not found! {}".format(sound_path, pg.get_error()))
        return

    pg.mixer.music.play()


def sound_init():
    pg.mixer.init(44100, -16, 2, 2048)
    pg.mixer.music.set_volume(sound_volume)


def firmware_monitor():
    global sock, conn, printing, awaiting_baby_step

    while True:
        try:
            if not sock:
                try:
                    if debugging:
                        log_print("Connecting to {}...".format(duet_host))
                    sock = socket.create_connection((duet_host, 23), timeout=10)
                except:
                    sock = None

            if sock:
                log_print("Connection established. Pausing for firmware...")
                time.sleep(4.5)  # RepRapFirmware uses a 4-second ignore period after connecting
                conn = SimpleLineProtocol(sock)

                timelapse_folder = None
                current_layer = -1
                current_z = 0
                max_z = 0
                last_baby_step = -1000.0
                last_layer = -1
                image_count = 0
                gcode_filename = ''
                start_time = time.time()
                next_status_time = start_time + 1.0
                next_blink_time = start_time + 5.0
                last_picture_path = ""
                data = None
                message = None
                sent_error_msg = False
                sent_pause_msg = False

                while sock:
                    current_time = time.time()
                    status = "I"

                    try:
                        data,message = conn.read_data()

                        if data:
                            if debugging:
                                run_time = time.time() - start_time
                                if run_time > 3 and image_count <= minimum_image_count:
                                    data['status'] = 'P'
                                    data['currentLayer'] = data['currentLayer'] + 1
                                    data['coords']['xyz'][2] = data['currentLayer'] * 0.2

                            status = data['status']
                            current_layer = data['currentLayer']
                            current_z = data['coords']['xyz'][2]

                            temp_fault = False
                            temps = data['temps']
                            bed_state = temps['bed']['state']

                            if bed_state == 3:
                                temp_fault = True
                            else:
                                heads = temps.get("heads")
                                if heads:
                                    states = heads.get("state")
                                    if states:
                                        for state in states:
                                            if state == 3:
                                                temp_fault = True
                                                break

                            if temp_fault:
                                status = '*'

                            if status == 'P':
                                if current_z > 0 and current_z < max_z + 10:
                                    max_z = current_z

                                current_baby_step = float(data['params']['babystep'])

                                if last_baby_step == -1000 and current_baby_step == 0:
                                    last_baby_step = 0;
                                elif last_baby_step != -1000 and last_baby_step != current_baby_step:
                                    if current_baby_step > last_baby_step:
                                        play_sound("click-down.wav")
                                    else:
                                        play_sound("click-up.wav")
                                    last_baby_step = current_baby_step
                                    awaiting_baby_step = False

                        if message:
                            if message.startsWith('sound:'):
                                play_sound(message[6:])

                        if not data and not message and current_time > next_status_time:
                            conn.write('M408 S4')
                            delay_time = 0.1 if awaiting_baby_step else printer_status_delay
                            next_status_time - current_time + delay_time

                    except:
                        sock.close()
                        sock = None
                        conn = None

                    if status == 'I' and not timelapse_folder and current_time > next_blink_time:
                        set_active_light(True)
                        time.sleep(0.003)
                        set_active_light(False)
                        next_blink_time = current_time + 5.0

                    if debugging:
                        log_print("Printer status: " + status)
                        if data:
                            # log_print(data)
                        if message:
                            # log_print("Message: " + message)

                    if status == 'P' and not timelapse_folder:
                        conn.write('M36')
                        file_info = conn.read_json_line()

                        if debugging:
                            file_info['fileName'] = 'SampleName'
                        else:
                            start_time = time.time()

                        filename = file_info['fileName']
                        gcode_filename = os.path.splitext(os.path.basename(filename))[0]
                        timelapse_folder = "{}/images/{}-{}".format(snapshot_folder, current_time_string(), gcode_filename)
                        os.makedirs(timelapse_folder)
                        set_active_light(True)
                        printing = True
                        log_print("New timelapse folder created: {}".format(timelapse_folder))
                        log_print("Waiting for layer changes...")

                    if status == 'I' and timelapse_folder:
                        if create_movie:
                            if image_count > minimum_image_count or debugging:
                                make_a_movie(gcode_filename, timelapse_folder, long(time.time() - start_time), last_picture_path, max_z)
                            else:
                                log_print("Movie too short - canceling")
                                shutil.rmtree(timelapse_folder)

                        timelapse_folder = None
                        last_layer = -1
                        last_picture_path = ''
                        last_baby_step = -1000.0
                        printing = False
                        awaiting_baby_step = False
                        if not debugging:
                            image_count = 0
                        log_print("Print finished.")

                    if status == 'I':
                        set_active_light(False)

                    if status == 'A' or status == 'S' and not sent_pause_msg:
                        msg_body = printer_name + ": PAUSED!\nProbable filament error."
                        send_sms(msg_body)
                        if debugging:
                            log_print(msg_body)
                        sent_pause_msg = True

                    if status == '*' and not sent_error_msg:
                        msg_body = printer_name + ": HEATER FAULT!"
                        send_sms(msg_body)
                        if debugging:
                            log_print(msg_body)
                        sent_error_msg = True

                    if status == 'P' or status == 'I':
                        sent_pause_msg = False;
                        sent_error_msg = False;

                    if timelapse_folder:
                        if current_layer > last_layer:
                            last_picture_path = layer_changed(timelapse_folder, webcam_url)
                            image_count = image_count+1

                    if debugging:
                        last_layer = current_layer - 1
                        time.sleep(printer_status_delay)
                    elif sock:
                        last_layer = current_layer

        except Exception as e:
            # log_print('ERROR', e)
            traceback.print_exc()

        set_active_light(False)
        printing = False
        awaiting_baby_step = False

        if sock:
            log_print("Exception occured. Will restart after delay...")
            blink_error(5)
            time.sleep(10)
            sock.close()
            sock = None
            conn = None
        else:
            # if debugging:
            #     log_print("Unable to connect to printer. Will try again in 5 seconds...")
            time.sleep(5)


def button_down():
    global awaiting_baby_step

    if printing:
        awaiting_baby_step = True
        conn.write('M290 S' + baby_step_amount)


def button_up():
    global awaiting_baby_step

    if printing:
        awaiting_baby_step = True
        conn.write('M290 S-' + baby_step_amount)


################################################################################

if __name__ == "__main__":
    streamer = None

    try:
        log_print('Start Timelapse System')

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        GPIO.setup(led_pin, GPIO.OUT)
        set_active_light(False)

        sound_init()

        GPIO.setup(button_down_pin, GPIO.IN, pull_up_down=GPIO.GPIO.PUD_UP)
        GPIO.add_event_detect(button_down_pin, GPIO.FALLING, callback=button_down, bouncetime=100)
        GPIO.setup(button_up_pin, GPIO.IN, pull_up_down=GPIO.GPIO.PUD_UP)
        GPIO.add_event_detect(button_up_pin, GPIO.FALLING, callback=button_up, bouncetime=100)

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
