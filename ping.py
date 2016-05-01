#!/usr/bin/env python3

import webcam

webcam = webcam.Webcam()
router_ip_address = webcam.get_router_ip_address()
webcam.send_email('current ip address', router_ip_address)