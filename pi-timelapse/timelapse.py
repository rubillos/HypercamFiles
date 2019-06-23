import errno
import os
import sys
import threading
import subprocess
import shutil
from datetime import datetime
from time import sleep
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)

def create_timestamped_dir(dir):
    try:
        os.makedirs(dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

def create_movies_dir():
    try:
        os.makedirs('movies')
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

def capture_image(dir, image_number):
   # Capture a picture.
    subprocess.call(["fswebcam", "-r", "1280x720", "--no-banner", dir + '/image{0:05d}.jpg'.format(image_number)])
    #image.save(dir + '/image{0:05d}.jpg'.format(image_number))
    print '\nSaved image.\n'

def timelapse_capture():
    image_number = 0

    # Create directory based on current timestamp.
    dateStr = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    dir = os.path.join( sys.path[0], 'series-' + dateStr)
    create_timestamped_dir(dir)

    print '\nCreated directory ' + dir + ', start capturing...\n'

    # Kick off the capture process.
    while (GPIO.input(4) == 0):
        capture_image(dir, image_number)
        image_number = image_number+1
        sleep(1);

    result = 0

    print '\nTimelapse done.\n'
 
    if (image_number > 8):
        print '\nCreating video.\n'
        result = os.system('avconv -framerate 30 -i ' + dir + '/image%05d.jpg -vf format=yuv420p -b:v 5000k ' + 'movies/' + dateStr + '.mp4')

    if (result == 0):
        shutil.rmtree(dir);

create_movies_dir()

GPIO.setup(4, GPIO.IN, pull_up_down=GPIO.PUD_UP)  

while (1):
    try:  
        print "Waiting for falling edge on port 4"  
        GPIO.wait_for_edge(4, GPIO.FALLING)  
        print "Falling edge detected. Start timelapse."
        print GPIO.input(4)
        timelapse_capture()
    except OSError as e:
        GPIO.cleanup()

