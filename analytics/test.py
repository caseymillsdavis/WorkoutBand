#!/usr/bin/env python
#Get acceleration data from Chronos watch.
#Taken from info posted at: http://e2e.ti.com/support/microcontrollers/msp43016-bit_ultra-low_power_mcus/f/166/t/32714.aspx
#
#FIXED: In old version I had the x and z value switched around.
#
#
# Copyright (c) 2010 Sean Brewer 
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
#
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
#
#
#If you want you may contact me at seabre986@gmail.com
#or on reddit: seabre
#


import serial
import serial.tools.list_ports
import array
import re

def startAccessPoint():
    return array.array('B', [0xFF, 0x07, 0x03]).tostring()

def accDataRequest():
    return array.array('B', [0xFF, 0x08, 0x07, 0x00, 0x00, 0x00, 0x00]).tostring()

def printData(dataString):
    if ord(dataString[0]) != 0 and ord(dataString[1]) != 0 and ord(dataString[2]) != 0:
        print "x: " + str(ord(dataString[0])) + " y: " + str(ord(dataString[1])) + " z: " + str(ord(dataString[2]))
    

x = serial.tools.list_ports.comports()
for element in x:
    if (re.search("/tty.usbmodem", element[0])):
        try:
            ser = serial.Serial(element[0], 115200, timeout = 1)
            print "connected to watch"
        except serial.SerialException:
            print "no connection"

#ser = serial.Serial('/dev/tty.usbmodem001', 115200, timeout = 1)

#Open COM port 6 (check your system info to see which port
#yours is actually on.)
#argments are 5 (COM6), 115200 (bit rate), and timeout is set so
#the serial read function won't loop forever.
#ser = serial.Serial(1,115200,timeout=1)

#Start access point
ser.write(startAccessPoint())

dataList = []

print "reached here"
while True:
    try:
        #Send request for acceleration data
        sneener = ser.write(accDataRequest())
        accel = ser.read(7)
        #dataList.append(accel)
        printData(accel)
    except KeyboardInterrupt:
        ser.close()
        break
    
    
    
ser.close()
