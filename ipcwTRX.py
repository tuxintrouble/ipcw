#!/usr/bin/python3
# -*- coding: utf-8 -*-

#Author: Sebastian Stetter  (DJ5SE)
#License GPL v3

#This file implements ipcwTRX trasceiver for NodeMCU / MicroPython

import machine, network, utime as time
from ipcw import *

DEBUG=1
### configuration ###
tx_url = '255.255.255.255' #can be replace with a relay server 
port = 7373
s_ssid = ''
s_key = ''
ap_ssid = 'ipcw_ap'
ap_key = 'ipcw'
ap_authmode = 0 #0 open, 1 wep, 2 wpa-psk, 3 WPA2, 4 wpa/wpa2-psk
wpm = 20
tx_sidetone = 550
rx_sidetone = 600
volume=500 #50%
txrx_delay = 500 #ms

###Pins####
sidetone_pin = 12
left_paddle_pin = 5
right_paddle_pin = 4

pwm = machine.PWM(machine.Pin(sidetone_pin))
left_paddle = machine.Pin(left_paddle_pin, mode=machine.Pin.IN, pull=machine.Pin.PULL_UP)
right_paddle = machine.Pin(right_paddle_pin, mode=machine.Pin.IN, pull=machine.Pin.PULL_UP)

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

def setup_network():
    global ip_address
    sta_if = network.WLAN(network.STA_IF)
    ap_if = network.WLAN(network.AP_IF)
    sta_if.active(True)
    networks = sta_if.scan()
    debug(networks[0])
    #check if we can connect to s_ssid
    if s_ssid.encode() in [n[0] for n in networks]:
        debug("try connect to %s" %s_ssid )
        #connect to given ssid
        
        sta_if.connect(s_ssid,s_key)
        time.sleep(3)
        if sta_if.isconnected():
            ip_address = sta_if.ifconfig()[0]
            debug(sta_if.ifconfig()[0])
            return sta_if.ifconfig()[0]
        else:
            ip_address = None
            return None
    
    elif ap_ssid.encode() in [n[0] for n in networks]: #try if we find network named 'ipcw_ap'
        debug("try ipcw_ap")
        sta_if.connect(ap_ssid,ap_key)
        time.sleep(3)
        if sta_if.isconnected():
            ip_address = sta_if.ifconfig()[0]
            return sta_if.ifconfig()[0]
        else:
            ip_address = None
            return None

    #setup access_point
    else:
        debug("make AP")
        ap_if.active(True)
        ap_if.config(essid=ap_ssid, password=ap_key, authmode=ap_authmode)
        time.sleep(4)
        ip_address = ap_if.ifconfig()[0]
        sta_if.active(False)
        return ap_if.ifconfig()[0]

        
def setup_socket():
    #see if we have an ip address
    if ip_address:
        socket = ipcwSocket((ip_address,port))
        return True
    else:
        return False


def sidetone(freq, duration):
    #code for PWM side tone here
    pwm.duty(0)
    pwm.freq(freq)
    pwm.duty(volume)
    time.sleep_ms(duration)
    pwm.duty(0)

def process_key():
    '''checks the key io pins and handles keying,sidetone, as well as character recognition'''
    pass

def play_string_as_morse(string, freq, wpm):
    '''plays the given string as morse code'''
    ell=ditlen(wpm)
    for c in string:
        if c ==' ':
            time.sleep_ms(ell*6) #wordspacing
            debug('<space>')
        else:
            debug(c)
            for e in morse[c.lower()]:
                if e == '.':
                    sidetone(freq,ell)
                    time.sleep_ms(ell)
                    debug(e)
                else:
                    sidetone(freq,ell*3)
                    time.sleep_ms(ell)
                    debug(e)
            time.sleep_ms(ell*2) #charcter spacing only 2x because we have a charspace already


def play_recvd(unicodestring):
    '''play morse received via socket'''
    p,s,wpm= decode_header(unicodestring)
    ell = ditlen(wpm)
     
    bytestring = unicodestring.decode()
    bitstring = ''
    for byte in bytestring:
        integer = ord(byte)
        #bitstring += f'{integer:08b}'
        bitstring += zfill(bin(integer)[2:],8) #works in uPython
        
    m_payload = bitstring[14:] #we just need the payload here

    #play morse code elements
    for i in range(0, len(m_payload),2):
        sym = m_payload[i]+m_payload[i+1]
        debug(sym)
        if sym == '01': #a dit
            sidetone(rx_sidetone,ell)
            time.sleep_ms(ell)
        elif sym == '10': #a dah
            sidetone(rx_sidetone,ell*3)
            time.sleep_ms(ell)
        elif sym == '00': #eoc
            time.sleep_ms(ell*4)    
        elif sym == '11': #eow
            time.sleep_ms(ell*6)
            return
        else:
            pass
    
