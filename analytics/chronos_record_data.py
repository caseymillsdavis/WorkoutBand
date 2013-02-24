#!/usr/bin/env python
import serial
import serial.tools.list_ports
import sys
import time

# Buttons
#  1   = ON
#  17  = *
#  255 = OFF
#  33  = #
#  49  = up

BUTTON_STAR  = 0x11
BUTTON_POUND = 0x21
BUTTON_UP    = 0x31

SECOND_TO_MICROSECOND = 1000000

START_ACCESS_POINT          = "\xFF\x07\x03"
BEFORE_REQUEST_ACCEL_DATA   = "\xFF\x00\x04"+"\x00"
REQUEST_ACCEL_DATA          = "\xFF\x08\x07"+"\x00"*4
STOP_ACCESS_POINT           = "\xFF\x09\x03"
BACKGROUND_POLLING          = "\xFF\x20\x07"+"\x00"*4

def zero_accel_data(data):
    return all([x == 0 for x in data])

def read_data():
    header = [int(ord(byte)) for byte in ser.read(3)]
    data = []
    data_len = header[2] - 3
    if data_len > 0:
        data = [int(ord(byte)) for byte in ser.read(data_len)]

    return header + data

if __name__ == '__main__':
    ser = None
    for element in serial.tools.list_ports.comports():
        if "/tty.usbmodem" in element[0]:
            try:
                ser = serial.Serial(element[0], 115200, timeout=1)
                print "connected to watch"
            except serial.SerialException:
                pass
    if ser is None:
        print "No serial connection found. Bluetooth dongle probably not connected."
        sys.exit(1)

    ser.write(START_ACCESS_POINT)
    print read_data()

    # Read until there's nothing to read
    while len(ser.read(1)):
        pass

    wfid = None
    start_time = None
    writing = False
    data_idx = None
    filename = None
    while True:
        try:
            #ser.write(BACKGROUND_POLLING)
            #raw = read_data()
            #print raw

            ser.write(REQUEST_ACCEL_DATA)
            raw = read_data()
            
            # Try to determine order of btyes. We want to read the bytes as
            # [255, 6, 7, tt, x, y, z]
            #for i in xrange(len(raw)):
            #    if (raw[i] == 255 and 
            #        raw[(i+1) % len(raw)] == 6 and 
            #        raw[(i+2) % len(raw)] == 7):
            #        break
            #data_idx = [(i+3+j) % len(raw) for j in xrange(DATA_LENGTH)]
            #data = [raw[i] for i in data_idx]
            data = raw[3:]

            if data[0] != 0xFF:
                if not writing and data[0] == BUTTON_STAR:
                    writing = True
                    filename = time.strftime("%Y-%m-%d_%H-%M-%S.txt")
                    print "Creating file:", filename
                    wfid = open(filename, 'w')
                    start_time = time.time()

                if writing and data[0] == BUTTON_POUND:
                    writing = False
                    print "Closing file:", filename
                    writing = False
                    wfid.close()

                if not zero_accel_data(data[1:]):
                    if writing:
                        dt = long((time.time() - start_time) * SECOND_TO_MICROSECOND)
                        wfid.write(str(dt) + ',' + ','.join(map(str,data[1:])) + '\n')
                    else:
                        print data

        except KeyboardInterrupt:
            break

    print "closing"
    if writing:
        wfid.close()
    ser.write(STOP_ACCESS_POINT)
    ser.close()

