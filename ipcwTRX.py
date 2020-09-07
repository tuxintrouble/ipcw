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
iambic_mode='a'
tx_sidetone = 550
rx_sidetone = 600
volume=500 #50%
txrx_delay = 500 #ms

### Pins ###
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

left_paddle_closed = False
right_paddle_closed = False
last_paddle_closed = None
last_paddle_released = None
last_key_time=None

keyer_buffer=''
sidetone_stop_time=None
silence_stop_time=None
ipcwsocket = None
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
    global ipcwsocket
    if ip_address:
        ipcwsocket = ipcwSocket((ip_address,port))
        return True
    else:
        return False


def sidetone(freq, duration):
    '''emits a sidetone of given freq for duration'''
    ell = ditlen(wpm)
    pwm.duty(0)
    pwm.freq(freq)
    pwm.duty(volume)
    sidetone_stop_time = time.ticks_ms + duration
    silence_stop_time =  time.ticks_ms + duration + ell  #silence after the tone blocks new sidetone

def stop_sidetone():
	'''this stops the sidetones. called by meinloop'''
	if sidetone_stop_time and time.ticks_ms() >= sidetone_stop_time:
		pwm.duty(0)
		sidetone_stop_time = None
	if silence_stop_time and time.ticks_ms() >= silence_stop_time:
		silence_stop_time = None


#called on paddle events
def left_paddle_pressed():
	process_keyer('left')

def left_paddle_released():
	pass

def right_paddle_pressed():
	process_keyer('right')

def right_paddle_released():
	pass


def process_paddles():
    '''check key pins for changes and change states, called by mainloop'''
	global left_paddle_closed
	global right_paddle_close
	global last_paddle_closed
	global last_paddle_released

    if left_paddle() and not left_paddle_closed:
    	left_paddle_pressed()
    	left_paddle_closed = True
    	last_paddle_closed = 'left'

    if not left_paddle() and left_paddle_closed:
    	left_paddle_released()
    	left_paddle_closed = False
    	last_key_time=time.ticks_ms()
    	last_paddle_released = 'left'

    if right_paddle() and not right_paddle_closed:
    	right_paddle_pressed()
    	right_paddle_closed = True
    	last_paddle_closed='right'

    if not right_paddle() and right_paddle_closed:
    	right_paddle_released()
    	right_paddle_closed = False
    	last_key_time=time.ticks_ms()
 		last_paddle_released = 'right'

def process_keyer_buffer():
	'''handles complete words, depending on what mode we are in. Only called by process_keyer()'''
	global keyer_buffer

	if keyer_buffer != '':
		#todo: check if we are in menu mode so see where the word must go
		#todo: encoding for sending through  socket
		if status_tx:
			#send it - we need to implement a new encode_morse finction  to deal with binary elements
			pass
		elif status_menu:
			#handle menu commands here
			pass
		keyer_buffer=''


def process_keyer(caller):
	'''this function is called whenever a key is pressed. it has it'S own loop that is ended when it detects EOW'''

	global keyer_buffer
	global last_key_time
	ell = ditlen(wpm)

	while right_paddle_closed or left_paddle_closed:
		if caller == 'right': #start with a dah
			if right_paddle_closed and not silence_stop_time: #sst is always longer than the side tone, so this check covers both
				keyer_buffer += '10'
				sidetone(tx_sidetone,ell*3)
			if left_paddle_closed and not silence_stop_time:
				keyer_buffer += '01'

		elif caller == 'left': #start with a dit

			if left_paddle_closed and not silence_stop_time:
				keyer_buffer += '01'

			if right_paddle_closed and not silence_stop_time: 
				keyer_buffer += '10'
				sidetone(tx_sidetone,ell*3)

	#no key pressed anymore lets check for how long and see if characteror word
	if 	last_key_time and time.ticks_ms() >= last_key_time + (ell*7):
		#word
		keyer_buffer += '11'
		last_key_time = None
		process_keyer_buffer()

	if 	last_key_time and time.ticks_ms() >= last_key_time + (ell*3):
		#character
		keyer_buffer += '00'
		last_key_time = None
	#TODO: iambic modes??? 


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
    global keyer_buffer
    global state_tx
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
    #changed sleep times  for compatibility with nonblocking sidetone, blocking through receiving a word
    for i in range(0, len(m_payload),2):
        sym = m_payload[i]+m_payload[i+1]
       debug(sym)
        if sym == '01': #a dit
            sidetone(rx_sidetone,ell)
            time.sleep_ms(ell*2) #dit+space
        elif sym == '10': #a dah
            sidetone(rx_sidetone,ell*4) #dah+space
            #time.sleep_ms(ell)
        elif sym == '00': #eoc
            time.sleep_ms(ell*2) #eoc - 1space from previous element
        elif sym == '11': #eow
            time.sleep_ms(ell*6) #eow - 1space from previous element
            return
        else:
            pass

def receive()
	'''checks for incomming messages and receives them '''
	global state_tx
	global ipcwsocket

	if not state_tx or state_menu:
		play_recvd(ipcwsocket.recv())


def mainloop():
	receive()
	process_keyer()#process keying
	process_paddles()#process paddle changes
	stop_sidetone()#checks whether we need to stop a sidetone


if __name__ == '__main__':
	setup_network()
	setup_socket()

	while True:
		mainloop()
