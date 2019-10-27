led_pin = 23
printer_status_delay = 3.0
minimum_image_count = 20
initial_wait = 10

button_down_pin = 12
button_up_pin = 13
baby_step_amount = 0.02

sound_volume = 1.0

duet_host = "192.168.7.250" # address of the Duet Wifi or Duet Ethernet

snapshot_folder = "/home/pi/timelapse-movies" # folder to place final movies and temporary images into
sounds_folder = "/home/pi/sounds"

mjpg_streamer_folder = "/home/pi/installs/mjpg-streamer/mjpg-streamer-experimental" # location of mjpg_streamer
start_mjpg_streamer = "sudo ./mjpg_streamer -o 'output_http.so -w ./www' -i 'input_raspicam.so -x 972 -y 1296 -fps 15 -quality 95 -awb tungsten -ev -1 -mm matrix -rot 90'"
webcam_url = "http://127.0.0.1:8080/?action=snapshot" # url for retrieving images from mjpg_streamer

create_movie = True
encoding_options = "-b:v 10M -minrate 3M -maxrate 15M -bufsize 15M -c:v h264_omx -vf format=yuv420p -preset slow -crf 18 -profile:v -bf 2 -coder 1 -threads 4 -cpu-used 0"


# Array of z heights and crop factors (from the top of frame) to be processed using FFMPEG
crop_factors = ((0, 0.23), (50, 0.45), (100, 0.74), (200, 0.82), (300, 1.0))

send_twilio_sms = True
twilio_account_sid = "acccount-sid-goes-here"
twilio_auth_token  = "twilio-auth-token-goes-here"
twilio_to_number = "+12223334444"
twilio_from_number = "+12223334444"

send_email = True
smtp_port = 465  # For SSL
smtp_server = "outgoing-mail-server"
printer_name = "Hypercube"
sender_email = "mysendingemailaddress.com"
sender_from = "Hypercam <hypercube@mysendingemailaddress.com>"
sender_password = "password"
receiver_email = '"Target User Name"<targetemailaccount@something.com>'
