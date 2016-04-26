#!/usr/bin/env python3

import configparser
import logging
import os
import requests
import smtplib
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)
handler = logging.FileHandler('webcam.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

config = configparser.ConfigParser()
config.read('webcam.ini')

def get_file_ip_address():
    file_name = 'ipaddress'
    if os.path.isfile(file_name):
        file = open('ipaddress', 'r')
        ip_address = file.read()
        file.close()
        logger.debug('file ip address is %s' % ip_address)
        return ip_address

def set_file_ip_address(ip_address):
    file_name = 'ipaddress'
    if os.path.isfile(file_name):
        file = open('ipaddress', 'w')
        file.write(ip_address)
        file.close()
        logger.info('changed file ip address to %s' % ip_address)

def get_router_ip_address():
    request = requests.get('http://ipecho.net/plain')
    if request.status_code == 200:
        ip_address = request.text
        logger.debug('router ip address is %s' % ip_address)
        return ip_address

def send_email(subject, message):
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

def update_noip(ip_address):
    url = 'https://dynupdate.no-ip.com/nic/update?hostname=%s&myip=%s' % (config['DEFAULT']['noip.hostname'], ip_address)
    headers = {'Authorization': 'Basic %s' % config['DEFAULT']['noip.authorization'], 'User-Agent': '%s' % config['DEFAULT']['noip.useragent']}
    request = requests.get(url, headers=headers)
    if request.status_code == 200:
        logger.info('changed no-ip address to %s' % ip_address)
        return True
    else:
        logger.error('problem updating no-ip address: %s' % request.text)
        return False

router_ip_address = get_router_ip_address()
file_ip_address = get_file_ip_address()
if (router_ip_address != file_ip_address):
    if (update_noip(router_ip_address)):
        set_file_ip_address(router_ip_address)
        send_email('ip address changed', router_ip_address)
