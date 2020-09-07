#!/usr/bin/python3
# -*- coding: utf-8 -*-

#Author: Sebastian Stetter  (DJ5SE)
#License GPL v3

#This file implements ipcwTRX trasceiver for NodeMCU / MicroPython

import machine, network, utime as time
from ipcw import *

### configuration ###
tx_url = '255.255.255.255'
port = 7373
s_ssid = ''
s_key = ''
ap_ssid = 'ipcw_ap'
ap_key = 'ipcw'
ap_wifi_ch = 11
wpm = 20
tx_sidetone = 550.0
rx_sidetone = 600.0
txrx_delay = 500 #ms

###Pins####
sidetone_pin = 15
left_paddle_pin = 1
right_paddle_pin = 2
###########
# state variables #
ip_address = None #own ip address, will be set by setup_server function
state_tx = False #are we sending?
state_menu = False #are we in the menu?
dit_down = False
dah_down = False
last_lever_down = None
last_key_time=None
###########

def setup_network(ssid='ipcw_ap', key='ipcw'):
    try: #only if we are in uPython
        import network
        #check if we have a ssid different than 'ipcw_ap'
        if not ssid == 'ipcw_ap':
            #connect to given ssid
            pass
            return True
        elif False: #try if we find network named 'ipcw_ap'
            try:
                #to connect to it using standard credentials
            except:
                continue
            return True
        else:
            #we seem to be first, lets create an access point named 'ipcw_ap' for other devices
            return True

        
def setup_gpios():
    try:
        import machine
        #setup the pins and pwm for sidetone here
        
        return True
    except:
        #not on uPython
        return False

def setup_server():
    #see if we have an ip address
    if ip_address:
        socket = ipcwSocket((ip_address,port))
        return True
    else:
        return False


def sidetone(freq, duration)
    #code for PWM side tone here
    pass

def process_key():
    '''checks the key io pins and handles keying,sidetone, as well as character recognition'''
    pass

def play_string_as_morse(string, freq, wpm):
    '''plays the given string as morse code'''
    ell=ditlen(wpm)
    for c in string:
        if c ==' ':
            utime.sleep_ms(ell*6) #wordspacing
        else:
            for e in morse[c.lower()]:
                if e == '.':
                    sidetone(freq,ell)
                    time.sleep_ms(ell)
                else:
                    sidetone(freq,ell*3)
                    time.sleep_ms(ell)
    utime.sleep(ell*2) #charcter spacing only 2x becaus ewe have a charspace already


def play_recvd(data):
    '''play morse received via socket'''
    p,s,wpm= decode_header(data)
    ell = ditlen(wpm)
     
    bytestring = data.decode()
    bitstring = ''
    for byte in bytestring:
        integer = ord(byte)
        bitstring += f'{integer:08b}'
        
    m_payload = bitstring[14:] #we just need the payload here

    #play morse code elements
    for i in range(0, len(m_payload),2):
        sym = m_payload[i]+m_payload[i+1]

        if sym == '01': #a dit
            sidetone(rx_sidetone,ell)
            time.sleep(ell)
        elif sym == '10': #a dah
            sidetone(rx_sidetone,ell*3)
            time.sleep(ell)
        elif sym == '00': #eoc
            time.sleep(ell*4)    
        elif sym == '11': #eow
            time.sleep(ell*6)
    
