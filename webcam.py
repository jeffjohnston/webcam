import configparser
import logging
import os
import requests
import smtplib
import picamera
from time import sleep
from email.mime.text import MIMEText
import RPi.GPIO as GPIO
import time
import datetime as dt
import subprocess
import socket
import threading
from threading import Thread

config = configparser.ConfigParser()
config.read('webcam.ini')

logger = logging.getLogger(__name__)
handler = logging.FileHandler(config['DEFAULT']['log.file'])
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

class Webcam:

    def get_file_ip_address(self):
        file_name = 'ipaddress'
        if os.path.isfile(file_name):
            file = open('ipaddress', 'r')
            ip_address = file.read()
            file.close()
            logger.debug('file ip address is %s' % ip_address)
            return ip_address

    def set_file_ip_address(self, ip_address):
        file_name = 'ipaddress'
        if os.path.isfile(file_name):
            file = open('ipaddress', 'w')
            file.write(ip_address)
            file.close()
            logger.info('changed file ip address to %s' % ip_address)

    def get_router_ip_address(self):
        request = requests.get('http://ipecho.net/plain')
        if request.status_code == 200:
            ip_address = request.text
            logger.debug('router ip address is %s' % ip_address)
            return ip_address

    def send_email(self, subject, message):
        fromaddr = config['DEFAULT']['mail.from']
        toaddrs  = config['DEFAULT']['mail.to']

        msg = MIMEText(message)
        msg['Subject'] = subject
        msg['From'] = fromaddr
        msg['To'] = toaddrs

        username = config['DEFAULT']['smtp.username']
        password = config['DEFAULT']['smtp.password']

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(username, password)
        server.sendmail(fromaddr, toaddrs, msg.as_string())
        server.quit()

    def update_noip(self, ip_address):
        url = 'https://dynupdate.no-ip.com/nic/update?hostname=%s&myip=%s' % (config['DEFAULT']['noip.hostname'], ip_address)
        headers = {'Authorization': 'Basic %s' % config['DEFAULT']['noip.authorization'], 'User-Agent': '%s' % config['DEFAULT']['noip.useragent']}
        request = requests.get(url, headers=headers)
        if request.status_code == 200:
            logger.info('changed no-ip address to %s' % ip_address)
            return True
        else:
            logger.error('problem updating no-ip address: %s' % request.text)
            return False

    def main(self):
        camera = picamera.PiCamera()
        camera.resolution = (1024, 768)
        camera.exposure_mode = 'sports'
        camera.vflip = True
        camera.exposure_mode = 'auto'
        camera.metering = 'average'
        sleep(3)

        snapshot = Snapshot(camera)
        snapshot.start()

        server_socket = ServerSocket(camera)
        server_socket.start()

    def pic(self, camera):
        timestamp = dt.datetime.now().strftime('%m/%d %H:%M')
        timestamp += " (" + self.get_temp() + ")"
        camera.annotate_text = timestamp

        camera.capture('/var/www/html/camera.jpg')

    def snapshot(self):
        camera = picamera.PiCamera()
        camera.resolution = (1024, 768)
        camera.exposure_mode = 'sports'
        camera.vflip = True
        camera.exposure_mode = 'auto'
        camera.metering = 'average'
        sleep(3)

        timestamp = dt.datetime.now().strftime('%m/%d %H:%M')
        timestamp += " (" + self.get_temp() + ")"
        camera.annotate_text = timestamp

        camera.capture('/var/www/html/camera.jpg')

    def get_temp(self):
        try:
            output = subprocess.check_output(["/opt/vc/bin/vcgencmd", "measure_temp"])
            text = output.decode('utf-8')
            return text[5:-1]
        except:
            return ""

    def stream(self):
        camera = picamera.PiCamera()
        camera.resolution = (1024, 768)
        camera.exposure_mode = 'sports'
        camera.vflip = True
        camera.exposure_mode = 'auto'
        camera.metering = 'average'
        sleep(3)

        server_socket = ServerSocket(camera)
        server_socket.start()

    def video(self):
        camera = picamera.PiCamera()
        camera.resolution = (1024, 768)
        camera.exposure_mode = 'sports'
        camera.vflip = True
        sleep(3)
        camera.start_recording('/home/mnrabbit/video.h264')
        sleep(20)
        camera.stop_recording()

    def motion(self):
        sensor = 4
        count = 0

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(sensor, GPIO.IN, GPIO.PUD_DOWN)

        previous_state = False
        current_state = False

        while True:
            time.sleep(0.1)
            previous_state = current_state
            current_state = GPIO.input(sensor)
            if current_state != previous_state:
                new_state = "HIGH" if current_state else "LOW"
                print("GPIO pin %s is %s" % (sensor, new_state))
                if (new_state == "HIGH"):
                    count = count+1
                    camera = picamera.PiCamera()
                    camera.resolution = (1024, 768)
                    camera.exposure_mode = 'sports'
                    camera.vflip = True
                    camera.exposure_mode = 'auto'
                    camera.metering = 'average'
                    sleep(2)
                    camera.capture('/home/mnrabbit/pics/motion-%d.jpg' % count)
                    camera.close()

class Snapshot(Thread):

    def __init__(self, camera):
        Thread.__init__(self)
        self.camera = camera

    def run(self):

        while True:
            timestamp = dt.datetime.now().strftime('%m/%d %H:%M')
            timestamp += " (" + self.get_temp() + ")"
            self.camera.annotate_text = timestamp

            if (self.camera.recording):
                logger.debug('take snapshot using video port')
                self.camera.capture('/var/www/html/camera.jpg', use_video_port=True)
            else:
                logger.debug('take snapshot')
                self.camera.capture('/var/www/html/camera.jpg')

            sleep(10)

    def get_temp(self):
        try:
            output = subprocess.check_output(["/opt/vc/bin/vcgencmd", "measure_temp"])
            text = output.decode('utf-8')
            return text[5:-1]
        except:
            return ""

class ServerSocket(Thread):

    def __init__(self, camera):
        Thread.__init__(self)
        self.camera = camera

    def run(self):
        logger.debug('stream server is started')

        server_socket = socket.socket()
        server_socket.bind(('0.0.0.0', 8000))
        server_socket.listen(0)

        try:
            while True:
                connection = server_socket.accept()[0]
                stream = Stream(self.camera, connection)
                stream.start()
        finally:
            logger.debug('stream server is stopped')
            server_socket.close()

class Stream(Thread):

    def __init__(self, camera, connection):
        Thread.__init__(self)
        self.camera = camera
        self.connection = connection

    def run(self):
        while True:
            try:
                logger.debug('start the stream')

                file = self.connection.makefile('wb')
                self.camera.start_recording(file, format='h264')
                self.camera.wait_recording(60)

                logger.debug('end the stream')
            except (BrokenPipeError, IOError, ConnectionResetError):
                logger.debug('error caught')
            finally:
                self.camera.stop_recording()
                self.connection.close()
                file.close()



