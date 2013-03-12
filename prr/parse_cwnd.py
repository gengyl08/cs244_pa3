#!/usr/bin/python

import sys
import os
from argparse import ArgumentParser

parser = ArgumentParser(description="Parse cwnd")
parser.add_argument('--dir',
                    dest="dir",
                    help="Directory to tcp_probe.txt",
                    required=True)

args = parser.parse_args()

probe = open(args.dir + "/tcp_probe.txt", 'r')
cwnd = open(args.dir + "/cwnd.txt", 'w')

lines = probe.readlines()

for line in lines:

    line = line.split(' ')
    if(line[1].startswith("10.0.0.1")):
        cwnd.write(line[0] + ' ' + line[6] + '\n')

probe.close()
cwnd.close()
