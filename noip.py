#!/usr/bin/env python3

import webcam

webcam = webcam.Webcam()

router_ip_address = webcam.get_router_ip_address()
file_ip_address = webcam.get_file_ip_address()
if (router_ip_address != file_ip_address):
    if (webcam.update_noip(router_ip_address)):
        webcam.set_file_ip_address(router_ip_address)
        webcam.send_email('ip address changed', router_ip_address)
