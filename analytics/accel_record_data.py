#!/usr/bin/env python
import serial
import serial.tools.list_ports
import sys
import time

if __name__ == '__main__':
    ser = None
    for element in serial.tools.list_ports.comports():
        if "/tty.usbserial" in element[0]:
            try:
                ser = serial.Serial(element[0], 9600, timeout=1)
                print "connected to watch"
            except serial.SerialException:
                pass
    if ser is None:
        print "No serial connection found. Bluetooth dongle probably not connected."
        sys.exit(1)

    now = time.time()
    while True:
        ser.read(1)
        new = time.time()
        if new - now > 0.03:
            break
        now = new
    ser.read(12)

    while True:
        try:
            data = [int(ord(x)) for x in ser.read(13)]
            print ",".join(map(str,data[-3:]))
        except KeyboardInterrupt:
            break

    print "closing"
    ser.close()

