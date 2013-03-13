#!/usr/bin/python

import sys
import os
from argparse import ArgumentParser
import matplotlib
matplotlib.use('Agg')
import pylab as plt

parser = ArgumentParser(description="Parse cwnd")

parser.add_argument('--input',
                    dest="input",
                    required=True)

parser.add_argument('--output',
                    dest="output",
                    required=True)


args = parser.parse_args()

probe = open(args.input, 'r')
lines = probe.readlines()
time = []
cwnd = []

for line in lines:

    line = line.split(' ')
    if(line[1].startswith("10.0.0.1")):
        time = time + [float(line[0])]
        cwnd = cwnd + [int(line[6])]

probe.close()
plt.plot(time, cwnd, 'bo')
plt.xlabel('time')
plt.ylabel('cwnd')
plt.savefig(args.output)

