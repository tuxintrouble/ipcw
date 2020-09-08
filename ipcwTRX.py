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

channels = [['255.255.255.255',7373,'LAN']]

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
state_menu = False #are we in the menu?
mode = 0 #0 off, 1 rx, 1 tx, 3 cmd
exec_cmd = None
cmd_entered_time = None
current_channel=1
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

def setup_network(): #TODO: change to take 'a' or network number int as argument and to user networks[[ssid,key,authmode]]
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
	global mode
	global exec_cmd
	global cmd_entered_time

	if keyer_buffer != '':
		#check if we are in menu mode so see where the word must go
		#0 off 1 rx 2 tx 3 cmd
		if mode == 1: #are we in rx mode?
			if keyer_buffer == '0101011101010111': # ..._... for cmd mode
				mode=3
				cmd_entered_time = time.ticks_ms()
				play_string_as_morse('e',900,25)
			else:
				mode = 2 #go in tx mode
				#send it - we need to implement a new encode_morse function  to deal with binary elements
			pass
		elif mode == 3:
			#handle menu commands here
			cmdstring = decode_buffer(keyer_buffer) #is none if buffer contains characters that cannot be decoded
			if cmdstring:
				if exec_cmd: #check if command - means this is a parameter (2nd part for a command)

					if exec_cmd == 'qrg':
						global current_channel
						if keyer_buffer == '?': #tell QRG
							play_string_as_morse(current_channel, cmd_sidetone, wpm)
						elif keyerbuffer and not len([i for i in keyerbuffer if not i.isdigit()]) #contains only numbers  #channel numbers
							global = channels
							if 0 <= int(keyer_buffer)-1 <= len(channels): #check if channel number is valid!!!
								current_channel = int(keyer_buffer)-1
								play_string_as_morse('r qrg %i %s' %(current_channel,channels[current_channel][0]), cmd_sidetone, wpm) #channel  no and name
							else:
								play_string_as_morse('?', cmd_sidetone, wp) #did not understand parameter
						else:
							play_string_as_morse('?', cmd_sidetone, wpm) #did not understand cmd
						exec_cmd = None
						keyer_buffer = ''
						mode = 3 #go back to cmd mode

					if exec_cmd == 'nc':
						global current_network
						if keyer_buffer == '?': #tell network
							play_string_as_morse(current_network, cmd_sidetone, wpm)
						elif keyer_buffer == 'a': #go to accesspoint mode
							pass #TODO execute setup network with 'a'
							play_string_as_morse('r ap', cmd_sidetone, wpm)
						elif keyer_buffer and not len([i for i in keyerbuffer if not i.isdigit()]) #contains only numbers  #network numbers
							global = networks
							if 0 <= int(keyer_buffer)-1 <= len(channels): #check if channel number is valid
								if not current_network == int(keyer_buffer)-1:
									current_network = int(keyer_buffer)-1
									#TODO: excute setup network with entry number' '
								play_string_as_morse('r %i %s' %(current_network ,networks[current_network][1]), cmd_sidetone, wpm)
							else:
								play_string_as_morse('?', cmd_sidetone, wp) #did not understand parameter
						else:
							play_string_as_morse('?', cmd_sidetone, wpm) #did not understand cmd
						exec_cmd = None
						keyer_buffer = ''
						mode = 3 #go back to cmd mode


					if exec_cmd == 'wpm':
						global wpm
						if keyer_buffer == '?': #tell wpm
							play_string_as_morse(wpm, cmd_sidetone, wpm) 
						elif keyerbuffer and not len([i for i in keyerbuffer if not i.isdigit()]) #contains only numbers
							if 4 < int(keyer_buffer) > 80:
								wpm = int(keyer_buffer)
								play_string_as_morse('wpm %i' %wpm, cmd_sidetone, wpm)
							else:
								play_string_as_morse('?', cmd_sidetone, wpm) #did not understand parameter
						else:
							play_string_as_morse('?', cmd_sidetone, wpm) #did not understand cmd
						exec_cmd = None
						keyer_buffer = ''
						mode = 3 #go back to cmd mode

					if exec_cmd == 'txt':
						global tx_sidetone
						if keyer_buffer == '?': #tell tx tone freq
							play_string_as_morse(tx_sidetone, cmd_sidetone, wpm) 
						elif keyerbuffer and not len([i for i in keyerbuffer if not i.isdigit()]) #contains only numbers
							if 100 < int(keyer_buffer) > 900:
								tx_sidetone = int(keyer_buffer)
								play_string_as_morse('txt %i' %tx_sidetone, cmd_sidetone, wpm)
							else:
								play_string_as_morse('?', cmd_sidetone, wpm) #did not understand parameter
						else:
							play_string_as_morse('?', cmd_sidetone, wpm) #did not understand cmd
						exec_cmd = None
						keyer_buffer = ''
						mode = 3 #go back to cmd mode


					if exec_cmd == 'rxt':
						global rx_sidetone
						if keyer_buffer == '?': #tell tx tone freq
							play_string_as_morse(rx_sidetone, cmd_sidetone, wpm) 
						elif keyerbuffer and not len([i for i in keyerbuffer if not i.isdigit()]) #contains only numbers
							if 100 < int(keyer_buffer) > 900:
								rx_sidetone = int(keyer_buffer)
								play_string_as_morse('rxt %i' %rx_sidetone, cmd_sidetone, wpm)
							else:
								play_string_as_morse('?', cmd_sidetone, wpm) #did not understand parameter
						else:
							play_string_as_morse('?', cmd_sidetone, wpm) #did not understand cmd
						exec_cmd = None
						keyer_buffer = ''
						mode = 3 #go back to cmd mode


					if exec_cmd == 'cmdt':
						global cmd_sidetone
						if keyer_buffer == '?': #tell tx tone freq
							play_string_as_morse(cmd_sidetone, cmd_sidetone, wpm) 
						elif keyerbuffer and not len([i for i in keyerbuffer if not i.isdigit()]) #contains only numbers
							if 100 < int(keyer_buffer) > 900:
								cmd_sidetone = int(keyer_buffer)
								play_string_as_morse('txt %i' %cmd_sidetone, cmd_sidetone, wpm)
							else:
								play_string_as_morse('?', cmd_sidetone, wpm) #did not understand parameter
						else:
							play_string_as_morse('?', cmd_sidetone, wpm) #did not understand cmd
						exec_cmd = None
						keyer_buffer = ''
						mode = 3 #go back to cmd mode

			#check for commands
				if cmdstring == 'qrt': #off
					exec_cmd = None
					mode = 0
				elif cmdstring == 'q': #leave cmd mode
					exec_cmd = None
					mode = 1 #go back to rx mode
				elif cmdstring == 'qtr': #announce time / depends on ntp and 
					play_string_as_morse('qtr - - -', cmd_sidetone, wpm)
					exec_cmd = None
					keyer_buffer = ''
					mode = 2 #go back to menu mode
				elif cmdstring == '?': #TODO: list commands
					play_string_as_morse("commands: ? q qrg qrt wpm rxt txt cmdt nc qtr",cmd_sidetone,wpm)
					exec_cmd = None
					keyer_buffer = ''
					mode = 2 #go back to menu mode
				elif cmdstring == 'qrg': #channel commads
					exec_cmd = 'qrg'
				elif cmdstring == 'wpm': #keyer speed
					exec_cmd == 'wpm'
				elif cmdstring == 'txt': #transmit side tone freq
					exec_cmd == 'txt'
				elif cmdstring == 'rxt': #receive tone freq
					exec_cmd == 'rxt'
				elif cmdstring == 'cmdt': #command tone freq
					exec_cmd == 'cmdt'
				elif cmdstring == 'nc': #network connect
					exec_cmd == 'nc'

			else:
				#we did not understand
				play_string_as_morse('?',cmd_sidetone,wpm)
			pass
		keyer_buffer=''


def process_keyer(caller):
	'''this function is called whenever a key is pressed. it has it'S own loop that is ended when it detects EOW'''

	global keyer_buffer
	global last_key_time
	global cmd_entered_time
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

	if mode == 3 and  if cmd_entered_time and time.ticks_ms() >= cmd_entered_time + 10000: #comand mode for longer than 10secs?
		mode = 1 #go back to rx mode
		sidetone(cmd_sidetone,200) #emit 200ms tone
		cmd_entered_time = None


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
    global mode 
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
	global mode
	global ipcwsocket

	if mode == 1:
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
