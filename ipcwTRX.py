#!/usr/bin/python3
# -*- coding: utf-8 -*-

#Author: Sebastian Stetter  (DJ5SE)
#License GPL v3

#This file implements ipcwTRX trasceiver for NodeMCU / MicroPython

import machine, network, utime as time
from ipcw import *

#TODO: implementation of load_config() and save_config()
#TODO: implement send_keyer_buffer()
#TODO: clean up redundancies in process_keyer_puffer()
#TODO: measure actial ADC battery levels with hardware
#TODO: testing...
#TODO: implement iambic modes and tune timing
#TODO: implement txrx_delay and recive blocking through modes (tx blocks rx, ...)
#TODO: implement webserver for configuration

DEBUG=1
### configuration ###
rx_port = 7373 #port for the receiver socket to listen on
ap_ssid = 'ipcw_ap'
ap_key = 'ipcw'
ap_authmode = 0 #0 open, 1 wep, 2 wpa-psk, 3 WPA2, 4 wpa/wpa2-psk
wpm = 20
iambic_mode='a' # a|b
tx_sidetone = 550
rx_sidetone = 600
cmd_sidetone = 800
volume = 500 #50% dutycycle
txrx_delay = 500 #ms

channels = [['255.255.255.255',7373,'LAN']]
networks = [
	[''ipcw_ap','ipcw'], #ssid, passphrase
]
### Pins ###
sidetone_pin = 12
left_paddle_pin = 5
right_paddle_pin = 4
battery_pin = 0

pwm = machine.PWM(machine.Pin(sidetone_pin))
left_paddle = machine.Pin(left_paddle_pin, mode=machine.Pin.IN, pull=machine.Pin.PULL_UP)
right_paddle = machine.Pin(right_paddle_pin, mode=machine.Pin.IN, pull=machine.Pin.PULL_UP)
batt = machine.ADC(0)

batt_warning_v = 3.6
batt_critical_v = 3.4

###########
# state variables #
ip_address = None #own ip address, set by  setup_network()
mode = 0 #0 off, 1 rx, 1 tx, 3 cmd
exec_cmd = None
cmd_entered_time = None
current_channel = channels[0] #default channel 0,
left_paddle_closed = False
right_paddle_closed = False
last_paddle_closed = None
last_paddle_released = None
last_key_time=None
keyer_buffer=''
#sidetone_stop_time=None
silence_stop_time=None
ipcwsocket = None
###########


def load_config():
	'''load config from file, if we dont have one, make one'''
	#TODO
		
	pass

def save_config():
	'''save variables to config file'''
	#TODO
	pass

def deep_sleep(msecs):
	'''put machine into deep sleep for msecs'''
	rtc = machine.RTC()
	rtc.irq(trigger=rtc.ALARM0, wake=machine.DEEPSLEEP)
	rtc.alarm(rtc.ALARM0, msecs)
	machine.deepsleep()

def check_battery():
	"periodically check battery voltage, issue warning  - lo batt - go to deepsleep if critical"
	if batt.read() <= batt_warning_v:
		play_string_as_morse("lo battery", cmd_sidetone, wpm)
	elif batt.read() <= batt_critical_v:
		mode = 0
		deep_sleep(60*5000)

def connect_to_network(network):
	'''connect to given network, returns True|False'''
    global ip_address
    sta_if = network.WLAN(network.STA_IF)
    ap_if = network.WLAN(network.AP_IF)
    sta_if.active(True)
    available_networks = sta_if.scan()
    debug(available_networks[0])
    #check if our network amongst the avalianble
    if network[0].encode() in [n[0] for n in available_networks]:
        debug("try connect to %s" %s_ssid )
        sta_if.connect(network[0],network[1]) #ssid, key
        time.sleep(3)
        if sta_if.isconnected():
            ip_address = sta_if.ifconfig()[0]
            debug(sta_if.ifconfig()[0])
            return True
        else:
            ip_address = None
            return False

def setup_accesspoint()
    '''setup access_point'''
    global ip_address
    global current_network
	debug("make AP")
	ap_if.active(True)
	#check if ap_name is already used
	if not sta_if.active():
		sta_if.active(True)
	available_networks =sta_if.scan()
	ssid = ap_ssid
	i = 1
	while ap_ssid.encode()in [n[0] for n in available_networks]:
		ssid = ap_ssid+'_%i' %i #try counting up till we get an exclusive ssid
		i +=1
    ap_if.config(essid=ssid, password=ap_key, authmode=ap_authmode)
    time.sleep(4)
    ip_address = ap_if.ifconfig()[0]
    sta_if.active(False)
    current_network = None


def setup_network(id=None): 
	'''takes an index number of a network in the list or an 'a' for ap-mode, sets up ap-mode as fallback'''
	global current_network
	global ip_address
	if id == None: #no id given - use first that works
		for network in networks:
			if connect_to_network(network):
				current_network = network
				ap_if.active(False) #deactivate accesspoint
				ip_address = sta_if.ifconfig()[0]
				break
			else:
				current_network = None
		#accesspoint as fallback
		if current_network = None:
			setup_accesspoint()
	elif id == 'a':
		setup_accesspoint()
	elif id and id != 'a':
		if connect_to_network[id -1]:
			current_network = network[id -1]
			ap_if.active(False) #deactivate accesspoint
			ip_address = sta_if.ifconfig()[0]
		else:
			current_network = None
		#accesspoint as fallback
		if current_network = None:
			setup_accesspoint()


def setup_socket():
    #see if we have an ip address
    global ipcwsocket
    if ip_address:
        ipcwsocket = ipcwSocket((ip_address,rx_port))
        return True
    else:
        return False

def sidetone(freq, duration):
    '''emits a sidetone of given freq for duration'''
    ell = ditlen(wpm)
    pwm.duty(0)
    pwm.freq(freq)
    pwm.duty(volume)
    timer = machine.Timer(1)
    timer.init(mode=Timer.ONE_SHOT, period=duration, callback=stop_sidetone)
    #sidetone_stop_time = time.ticks_ms + duration / ##we  use a timer now
    silence_stop_time =  time.ticks_ms + duration + ell  #silence after the tone blocks new sidetone TODO: maybe find a way to do this with timer?

def stop_sidetone():
	'''this stops the sidetones. called by meinloop'''
##	if sidetone_stop_time and time.ticks_ms() >= sidetone_stop_time:
	pwm.duty(0)
##		sidetone_stop_time = None
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
				#TODO: send it - we need to implement a new encode_morse function  to deal with binary elements
		elif mode == 3:
			#handle menu commands here
			cmdstring = decode_buffer(keyer_buffer) #is none if buffer contains characters that cannot be decoded
			if cmdstring:
				if exec_cmd: #check if command - means this is a parameter (2nd part for a command)
					if exec_cmd == 'qrg':
						global current_channel
						if keyer_buffer == '?': #tell QRG
							play_string_as_morse(current_channel, cmd_sidetone, wpm)
						elif keyerbuffer and not len([i for i in keyerbuffer if not i.isdigit()]): #contains only numbers  #channel numbers
							global channels
							if int(keyer_buffer)-1 >=0 and int(keyer_buffer)-1 <= len(channels): #check if channel number is valid!!!
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
							if current_network:
								play_string_as_morse('%i %s'%(networks.index(current_network)+1,current_network[0]), cmd_sidetone, wpm) #id ssid
							else:
								play_string_as_morse(ap_ssid, cmd_sidetone, wpm) #ssid of ap
						elif keyer_buffer == 'a': #go to accesspoint mode
							setup_network('a')
							play_string_as_morse('r ap %s' %ap_ssid, cmd_sidetone, wpm)
						elif keyer_buffer and not len([i for i in keyerbuffer if not i.isdigit()]): #contains only numbers  #network numbers
							global networks
							if int(keyer_buffer)-1 >= 0 and int(keyer_buffer)-1 <= len(channels): #check ifnetwork number is valid
								if not current_network == int(keyer_buffer)-1:
									setup_network(int(keyer_buffer)-1)
									play_string_as_morse('r %i %s' %(current_network ,networks[current_network][1]), cmd_sidetone, wpm)
							else:
								play_string_as_morse('?', cmd_sidetone, wp) #did not understand parameter
					else:
						play_string_as_morse('?', cmd_sidetone, wpm) #did not understand cmd
						exec_cmd = None
						keyer_buffer = ''
						mode = 3 #go back to cmd mode


					if exec_cmd == 'km':
						if keyer_buffer == '?': #tell keyer mode
							play_string_as_morse(keyer_mode, cmd_sidetone, wpm) 
						elif keyerbuffer and keyer_buffer == 'a' or keyer_buffer == 'b': #contains only numbers
							iambic_mode = keyer_buffer
							play_string_as_morse('keyer mode %s' %keyer_buffer, cmd_sidetone, wpm)
						else:
							play_string_as_morse('?', cmd_sidetone, wpm) #did not understand parameter
					else:
						play_string_as_morse('?', cmd_sidetone, wpm) #did not understand cmd
						exec_cmd = None
						keyer_buffer = ''
						mode = 3 #go back to cmd mode


					if exec_cmd == 'wpm':
						if keyer_buffer == '?': #tell wpm
							play_string_as_morse(wpm, cmd_sidetone, wpm) 
						elif keyerbuffer and not len([i for i in keyerbuffer if not i.isdigit()]): #contains only numbers
							if  int(keyer_buffer) >= 5 and int(keyer_buffer) <= 80:
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
						elif keyerbuffer and not len([i for i in keyerbuffer if not i.isdigit()]): #contains only numbers
							if  int(keyer_buffer) >= 100 and int(keyer_buffer) <= 900:
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
						elif keyerbuffer and not len([i for i in keyerbuffer if not i.isdigit()]): #contains only numbers
							if int(keyer_buffer) <= 100 and  int(keyer_buffer) <= 900:
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
						if keyer_buffer == '?': #tell tx tone freq
							play_string_as_morse(cmd_sidetone, cmd_sidetone, wpm) 
						elif keyerbuffer and not len([i for i in keyerbuffer if not i.isdigit()]): #contains only numbers
							if int(keyer_buffer) <=100 and  int(keyer_buffer) <= 900:
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
					save_config()
					play_string_as_morse('73 sk e e') #say good bye
					mode = 0
					deep_sleep(10000) #sleep for initial 10 secs
				elif cmdstring == 'qt': #leave cmd mode
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
				elif cmdstring == 'ip': #tell IP address
					play_string_as_morse("ip %s" %ip_address ,cmd_sidetone,wpm)
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
				elif cmdstring == 'km': #keyer mode a|b
					exec_cmd == 'km'

			else:
				#we did not understand
				play_string_as_morse('?',cmd_sidetone,wpm)
			pass
		keyer_buffer=''


def send_keyer_buffer():
	'''MOPP create header, add keyerbuffer and send it through the socket'''
	pass
	
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

	if mode == 3 and cmd_entered_time and time.ticks_ms() >= cmd_entered_time + 10000: #comand mode for longer than 10secs?
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

def receive():
	'''checks for incomming messages and receives them '''
	global mode
	global ipcwsocket

	if mode == 1:
		play_recvd(ipcwsocket.recv())

def wake():
	'''called by mainloop to check if device is on or off'''
	global mode
	if mode == 0:
		i=0
		while left_paddle() and right_paddle(): #paddles squeezed for at least 3secs
			t = time.sleep(3)
			if i <=2:
				i+=1
			else:
				mode = 2 #goto rx mode and continue in main()
				play_string_as_morse('...-... hello',cmd_sidetone, wpm)
		i=0
		else: #go backt to deep sleep for 6s
			deep_sleep(6000)


def setup():
	'''setup is called whenever we start the device or after we wake up'''
	check_battery()
	battery_timer = machine.Timer(4)
	battery_timer.freq(1)
	battery_timer.callback(check_Battery())

	load_config()

	if setup_network():
		setup_socket()
	else:
		play_string_as_morse("network error",cmd_sidetone,wpm)


def mainloop():
	receive()
	process_keyer() #process keying
	process_paddles() #process paddle changes
	stop_sidetone() #checks whether we need to stop a sidetone TODO: Maybe use timers for this?

if __name__ == '__main__':
	wake() #check if we should start device
	setup()
	while True:
		mainloop()
