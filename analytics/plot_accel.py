#!/usr/bin/env python
import sys
import numpy as np
from scipy.interpolate import interp1d
from scipy.integrate import quad
import matplotlib.pyplot as plt

def read_data(filename):
    data_list   = []
    t = 0
    with open(filename, 'r') as file:
        for line in file:
            raw = line.rstrip('\n').split(',')
            if len(raw) == 4:
                raw = map(float, raw)
                data_list.append([raw[0]/1000.,
                                  raw[1] - 255 if raw[1] > 127 else raw[1],
                                  raw[2] - 255 if raw[2] > 127 else raw[2],
                                  raw[3] - 255 if raw[3] > 127 else raw[3]])
            elif len(raw) == 3:
                raw = map(float, raw)
                data_list.append([t,
                                  raw[0] - 127,
                                  raw[1] - 127,
                                  raw[2] - 127])
                t += .02

    return np.array(data_list)

def plot(data, title):
    t, x, y, z = data.T
    axis = plt.subplot(5, 1, plot.counter, sharex=plot.prev_axis)
    if plot.counter == 1:
        plot.prev_axis = axis
    plot.counter += 1
    axis.plot(t, x, 'b-x', label='x')
    axis.plot(t, y, 'g-x', label='y')
    axis.plot(t, z, 'r-x', label='z')
    axis.grid(True)
    axis.legend()
    plt.title(title)
plot.prev_axis = None
plot.counter = 1

def derivative(data):
    t, x, y, z = data.T
    dt = np.diff(t)
    x = np.diff(x) / dt
    y = np.diff(y) / dt
    z = np.diff(z) / dt
    t = t[:-1] + dt
    return np.array((t, x, y, z)).T

def integrate(data):
    def integ(val):
        integ.tmp += val
        return integ.tmp

    t, x, y, z = data.T
    integ.tmp = 0.
    x = [integ(v) for v in x]
    integ.tmp = 0.
    y = [integ(v) for v in y]
    integ.tmp = 0.
    z = [integ(v) for v in z]

    return np.array((t, x, y, z)).T

def smooth(data, window='rect', winsize=3):
    t, x, y, z = data.T
    if window == 'rect':
        w = np.ones(winsize, 'd')
    else:
        w = eval('np.'+window+'(winsize)')

    t = t[winsize-1:]
    x = np.convolve(w/w.sum(), x, mode='valid')
    y = np.convolve(w/w.sum(), y, mode='valid')
    z = np.convolve(w/w.sum(), z, mode='valid')
    return np.array((t, x, y, z)).T

def interpolate(data, kind='linear', interval=20):
    t, x, y, z = data.T
    accel_x_intpl = interp1d(t, x, kind=kind)
    accel_y_intpl = interp1d(t, y, kind=kind)
    accel_z_intpl = interp1d(t, z, kind=kind)
    x_sample = np.linspace(min(t), max(t), long((max(t) - min(t)) / interval))

    t = x_sample
    x = accel_x_intpl(x_sample)
    y = accel_y_intpl(x_sample)
    z = accel_z_intpl(x_sample)
    return np.array((t, x, y, z)).T

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "Specify file to write"

    if len(sys.argv) > 2:
        fig = plt.figure(figsize=(16,12), dpi=120)

    raw = read_data(sys.argv[1])
    #plot(raw, 'Raw')

    #raw = interpolate(raw, interval=33)
    #plot(raw, 'Interpolated')

    data = raw

    data = smooth(raw, winsize=10)
    plot(data, 'Smooth')

    deriv = derivative(data)
    plot(deriv, 'Derivative')

    plot(smooth(deriv, winsize=10), 'Smooth Derivative')

    plot(np.absolute(data), 'Absolute')

    if len(sys.argv) > 2:
        plt.savefig(sys.argv[2])
    else:
        plt.show()

