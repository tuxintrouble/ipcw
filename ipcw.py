#!/usr/bin/python3
# -*- coding: utf-8 -*-

#Author: Sebastian Stetter  (DJ5SE)
#License GPL v3

#This file implements funktions for cw over the UDP protocol

import socket, time, os
from math import ceil

DEBUG=0

protocol_version = 1
serial = 1

morse = {"0" : "-----", "1" : ".----", "2" : "..---", "3" : "...--", "4" : "....-", "5" : ".....",
         "6" : "-....", "7" : "--...", "8" : "---..", "9" : "----.",
         "a" : ".-", "b" : "-...", "c" : "-.-.", "d" : "-..", "e" : ".", "f" : "..-.", "g" : "--.",
         "h" : "....", "i" : "..", "j" : ".---", "k" : "-.-", "l" : ".-..", "m" : "--", "n" : "-.",
         "o" : "---", "p" : ".--.", "q" : "--.-", "r" : ".-.", "s" : "...", "t" : "-", "u" : "..-",
         "v" : "...-", "w" : ".--", "x" : "-..-", "y" : "-.--", "z" : "--..", "=" : "-...-",
         "/" : "-..-.", "+" : ".-.-.", "-" : "-....-", "." : ".-.-.-", "," : "--..--", "?" : "..--..",
         ":" : "---...", "!" : "-.-.--", "'" : ".----."
    }

def debug(s):
    if DEBUG:
        print(s)


#make own zfill for uPython
def zfill(str,digits):
    '''we need to implement our own zfill for uPython)'''
    if len(str)>=digits:
        return str
    else:
        return ((digits - len(str)) * '0')+str


#make own ljust for uPython
def ljust(string, width, fillchar=' '):
    '''returns the str left justified, remaining space to the right is filed with fillchar, if str is shorter then width, original string is returned '''
    while len(string) < width:
        string += fillchar
    return string


def ditlen(wpm):
    '''calculates the length in ms of a morse code element for given words per minute'''
    return int(60000 / (50*wpm)) #60000s / (50 elements (as in PARIS) * WPM)


def encode_morse(text,wpm):
    '''creates an bytes for ending throught a socket'''

    """Protocol description:
    This may be compatible with the morserino protocol

    
    protocolversion: 2 bits
    serial number: 6 bits
    morse speed: 6 bits
    text: variable length of 2bit characters

    01 = dit
    10 = dah
    00 = End of Character
    11 = End of Word
    """

    global serial

    #create 14 bit header
    m = zfill(bin(protocol_version)[2:],2) #2bits for protocol_version
    m += zfill(bin(serial)[2:],6) #6bits for serial number
    m += zfill(bin(wpm)[2:],6) #6bits for words per minute

    #add payload
    for c in text:
        if c == ' ':
            continue #skip space characters

        for e in morse[c.lower()]:
            if e == '.':
                m += '01' #dit
            else:
                m += '10' #dah

        m += '00' #End of character
    m = m[0:-2] + '11' #End of word

    m = ljust(m,int(8*ceil(len(m)/8.0)),'0') #fill in incomplete byte

    res = ''
    for i in range(0, len(m),8):
        res += chr(int(m[i:i+8],2))

    serial +=1
    return res.encode()


def decode_header(unicodestring):
    '''converts a received morse code byte string and returns a list
    with the header info [protocol_v, serial, wpm]''' 
    bytestring = unicodestring.decode()
    bitstring = ''

    for byte in bytestring:
        integer = ord(byte)
        #bitstring += f'{integer:08b}'
        bitstring += zfill(bin(integer)[2:],8) #works in uPython
    
    m_protocol = int(bitstring[:2],2)
    m_serial = int(bitstring[3:8],2)
    m_wpm = int(bitstring[9:14],2)
    return [m_protocol, m_serial, m_wpm]


def decode_payload(unicodestring):
    '''converts a received morse code byte sting to text''' 
    bytestring = unicodestring.decode()
    bitstring = ''
    for byte in bytestring:
        integer = ord(byte)
        #bitstring += f'{integer:08b}'
        bitstring += zfill(bin(integer)[2:],8) #works in uPython
        
    m_payload = bitstring[14:] #we just need the payload here

    text = ''
    #parse morse code elements
    charbuffer ='' 
    for i in range(0, len(m_payload),2):
        sym = m_payload[i]+m_payload[i+1]

        if sym == '01': #a dit
            charbuffer += '.'
            
        elif sym == '10': #a dah
            charbuffer += '-'
            
        elif sym == '00': #eoc
            rec=0
            for key,value in morse.items():
                if value == charbuffer:
                    text = text + key
                    charbuffer=''
                    rec = 1
                    break
            if not rec: #unknown character
                text += '*'
                
        elif sym == '11': #eow
            rec=0
            for key,value in morse.items():
                if value == charbuffer:
                    text = text + key
                    charbuffer=''
                    rec=1
                    break
            if not rec: #unknown character
                text += '*'

            return text

        

class ipcwSocket():

    def __init__(self,url=('0.0.0.0',7373),timeout=10):
        self.serversock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.serversock.bind(url)
        self.serversock.settimeout(timeout)
        if not os.uname()[0].startswith("esp"): #disable for ESP systems
            self.serversock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, True)
        debug("Server created")


    def sendto(self, data, url):
        self.serversock.sendto(data,url)

    def recv(self):
        data=None
        try:
            data = self.serversock.recv(64)
        except:
            print("timeout")
        if data:
            #return[decode_header(data),decode_payload(data)]
            return data

if __name__ == "__main__":
    print(decode_payload(encode_morse('DJ5?E/p',20)))
    print(decode_header(encode_morse('DJ5?E/p',20)))
    s = ipcwSocket()
    #s.sendto(encode_morse('servertest',20),('255.255.255.255',7373))
    s.sendto(encode_morse('DJ5SE\p',20),('192.168.178.36',7373))

    time.sleep(0)
    print(s.recv())
    

