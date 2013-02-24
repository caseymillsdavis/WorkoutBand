#!/usr/bin/env python
import serial
import serial.tools.list_ports
import sys
import time
import requests
import json
import threading

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

# Sy magic
host_url = 'http://ec2-107-20-75-207.compute-1.amazonaws.com:3000'
rep_url = host_url + '/repetitions'

def update_to_sy(obj, workout_id=81):
    data = { "workout_id"    : workout_id,
             "exercise_type" : obj.name,
             "repetition"    : {"weight":obj.weight, "count":obj.count} }
    headers = {"Accept": "application/json", "Content-type": "application/json"}
    r = requests.post(rep_url, data=json.dumps(data), headers=headers)
    print r

def zero_accel_data(data):
    return all([x == 0 for x in data])

def read_data():
    header = [int(ord(byte)) for byte in ser.read(3)]
    data = []
    data_len = header[2] - 3
    if data_len > 0:
        data = [int(ord(byte)) for byte in ser.read(data_len)]

    return header + data

class Smooth:
    def __init__(self, size):
        self.size = size
        self.buff = []
        for idx in range(3):
            self.buff.append([0] * self.size)

    def update(self, sample):
        for idx in range(3):
            self.buff[idx].insert(0, sample[idx])
            self.buff[idx].pop()

        ret = [0] * 3
        for idx in range(3):
            for s in self.buff[idx]:
                ret[idx] += s
            ret[idx] /= float(self.size)

        return ret

class Sample:
    def __init__(self):
        self.time  = 0
        self.accel = [0] * 3
        self.deriv = [0] * 3

class SampleBuffer:
    def __init__(self):
        self.time   = []
        self.sraw = []
        self.sder = []
        self.smooth_raw = Smooth(10)
        self.smooth_der = Smooth(10)

    def update(self, raw):
        raw[0] = raw[0]/1000.
        for idx in range(1,4):
            raw[idx] = raw[idx] - 255 if raw[idx] > 127 else raw[idx]

        self.time.append(raw[0])
        self.sraw.append(self.smooth_raw.update(raw[1:]))

        der = [0] * 3
        if len(self.time) >= 2:
            dt = self.time[-1] - self.time[-2]
            for idx in range(3):
                der[idx] = (self.sraw[-1][idx] - self.sraw[-2][idx]) / dt
            self.sder.append(self.smooth_der.update(der))

    def last_sample(self):
        sample = Sample()
        sample.time  = self.time[-1]
        sample.accel = self.sraw[-1]
        if len(self.sder) > 0:
            sample.deriv = self.sder[-1]
        else:
            sample.deriv = [0] * 3
        return sample

class Curl:
    STATUS_START = 0
    STATUS_MID   = 1
    STATUS_END   = 2

    def __init__(self, weight=30):
        self.weight = weight
        self.name = "Biceps curl"

        self.count = 0
        self.status = self.STATUS_END

    def update_sample(self, sample):
        rep = 0
        y = sample.accel[1]
        print "Curl:", y, self.status
        if self.status is self.STATUS_END:
            if y > -38:
                self.status = self.STATUS_START
        elif self.status is self.STATUS_START:
            if y > 30:
                self.status = self.STATUS_MID
            elif y < -38:
                self.status = self.STATUS_END
        elif self.status is self.STATUS_MID:
            if y < -38:
                self.status = self.STATUS_END
                rep = 1
                self.count += 1
        return rep

    def reset(self):
        self.count = 0
        self.status = self.STATUS_END

class Butterfly:
    STATUS_START = 0
    STATUS_MID   = 1
    STATUS_END   = 2

    def __init__(self, weight=15):
        self.weight = weight
        self.name = "Butterfly"

        self.count = 0
        self.status = self.STATUS_END
        self.start_y = 0

    def update_sample(self, sample):
        rep = 0
        y  = sample.accel[1]
        z  = sample.accel[2]
        yd = sample.deriv[1]
        print "ButterfLy:", self.status, y, yd, z
        if self.status is self.STATUS_END:
            if yd > 0.05:
                self.status  = self.STATUS_START
                self.start_y = y
        elif self.status is self.STATUS_START:
            if z > 0:
                self.status = self.STATUS_MID
            elif y < self.start_y:
                self.status = self.STATUS_END
        elif self.status is self.STATUS_MID:
            if y < self.start_y:
                self.status = self.STATUS_END
                rep = 1
                self.count += 1
        return rep

    def reset(self):
        self.count = 0
        self.status = self.STATUS_END
        self.start_y = 0

class DeadLift:
    STATUS_START = 0
    STATUS_MID   = 1
    STATUS_END   = 2

    def __init__(self, weight=50):
        self.weight = weight
        self.name = "Deadlift"

        self.count = 0
        self.status = self.STATUS_END
        self.start_y = 0

    def update_sample(self, sample):
        rep = 0
        y  = sample.accel[1]
        yd = sample.deriv[1]
        print "Deadlift:", self.status, y, yd
        if self.status is self.STATUS_END:
            if yd > 0.05:
                self.status  = self.STATUS_START
                self.start_y = y
        elif self.status is self.STATUS_START:
            if y > -40:
                self.status = self.STATUS_MID
            elif y < -60:
                self.status = self.STATUS_END
        elif self.status is self.STATUS_MID:
            if y < self.start_y:
                self.status = self.STATUS_END
                rep = 1
                self.count += 1
        return rep

    def reset(self):
        self.count = 0
        self.status = self.STATUS_END
        self.start_y = 0

class RFIDSerial(threading.Thread):
    def __init__(self):
        self.dev = '/dev/tty.usbserial-FTFBF55L'
        self.running = True
        self.rfid = -1
        threading.Thread.__init__(self)

    def getRFID(self):
        return self.rfid

    def stop(self):
        self.running = False

    def run(self):
        ser = serial.Serial(self.dev, 9600, timeout=1)

        now = time.time()
        while True:
            ser.read(1)
            new = time.time()
            if new - now > 0.03:
                break
            now = new
        ser.read(12)

        while self.running:
            data = [int(ord(x)) for x in ser.read(13)]
            if len(data) > 10 and data[9] != self.rfid:
                self.rfid = data[9]
        ser.close()

RFID2WORKOUT = {70: 0, # Curl, 0xCF
                55: 1, # Butterfly, 0xA7
                54: 2  # Deadlift, 0xB6
                }

if __name__ == '__main__':
    rfid_ser = RFIDSerial()
    rfid_ser.start()

    ser = serial.Serial('/dev/tty.usbmodem001', 115200, timeout=1)
    if ser is None:
        print "No serial connection found. Bluetooth dongle probably not connected."
        sys.exit(1)

    ser.write(START_ACCESS_POINT)
    print read_data()

    # Read until there's nothing to read
    while len(ser.read(1)):
        pass

    start_time = None
    workingout = False

    # workouts
    curl         = Curl()
    fly          = Butterfly()
    deadlift     = DeadLift()
    workouts     = {0: curl, 1: fly, 2: deadlift}
    workout_type = 1
    rfid         = 0

    buff = SampleBuffer()
    while True:
        try:
            ser.write(REQUEST_ACCEL_DATA)
            raw = read_data()
            data = raw[3:]

            if rfid != rfid_ser.getRFID():
                if not workingout:
                    rfid = rfid_ser.getRFID()
                    if rfid == -1 or rfid == 255:
                        continue
                    workout_type =  RFID2WORKOUT[rfid]
                    print "Changed workout to:", workouts[workout_type].name
                else:
                    print "Cannot change workout until finishing current workout!"

            if data[0] != 0xFF:
                workout = workouts[workout_type]
                if not workingout and data[0] == BUTTON_STAR:
                    print "Starting rep"
                    workingout = True
                    start_time = time.time()
                    workout.reset()

                if workingout and data[0] == BUTTON_POUND:
                    workingout = False
                    print "Ending rep"
                    print "%s: %d times!" % (workout.name, workout.count)
                    update_to_sy(workout)

                if not zero_accel_data(data[1:]):
                    if workingout:
                        dt = long((time.time() - start_time) * SECOND_TO_MICROSECOND)
                        raw_sample = [dt] + data[1:]
                        buff.update(raw_sample)

                        if workout.update_sample(buff.last_sample()):
                            "REP!"
                    else:
                        pass
                        #print data

        except KeyboardInterrupt:
            break

    print "closing"
    rfid_ser.stop()
    rfid_ser.join()

    ser.write(STOP_ACCESS_POINT)
    ser.close()

