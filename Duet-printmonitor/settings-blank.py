led_pin = 23
printer_status_delay = 3.0
minimum_image_count = 20
initial_wait = 10

duet_host = "192.168.7.250" # address of the Duet Wifi or Duet Ethernet

snapshot_folder = "/home/pi/timelapse-movies" # folder to place final movies and temporary images into

mjpg_streamer_folder = "/home/pi/installs/mjpg-streamer/mjpg-streamer-experimental" # location of mjpg_streamer

# Options for mjpg-mjpg_streamer
# In this case the camera is rotated 90º, quality is 95, white balance is set to tungsten
start_mjpg_streamer = "sudo ./mjpg_streamer -o 'output_http.so -w ./www' -i 'input_raspicam.so -x 972 -y 1296 -fps 15 -quality 95 -awb tungsten -ev -1 -mm matrix -rot 90'"

webcam_url = "http://127.0.0.1:8080/?action=snapshot" # url for retrieving images from mjpg_streamer

create_movie = True
encoding_options = "-c:v h264_omx -vf format=yuv420p -b:v 15000k" # use hardware encoding, max 15MB/s

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
