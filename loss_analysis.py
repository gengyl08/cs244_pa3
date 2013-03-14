#!/usr/bin/python

import sys
import os
from argparse import ArgumentParser
import numpy as np
import matplotlib
matplotlib.use('Agg')
import pylab as plt
from math import sqrt

parser = ArgumentParser(description="Delay analysis.")
parser.add_argument('--input1',
                    dest="input1",
                    help="Data file",
                    required=True)

parser.add_argument('--input2',
                    dest="input2",
                    help="Data file",
                    required=True)

parser.add_argument('--output',
                    dest="output",
                    help="Output file",
                    required=True)

args = parser.parse_args()

def avg(s):
    "Compute average of list or string of values"
    if ',' in s:
        lst = [float(f) for f in s.split(',')]
    elif type(s) == str:
        lst = [float(s)]
    elif type(s) == list:
        lst = s
    return sum(lst)/len(lst)

def median(l):
    "Compute median from an unsorted list of values"
    s = sorted(l)
    if len(s) % 2 == 1:
        return s[(len(l) + 1) / 2 - 1]
    else:
        lower = s[len(l) / 2 - 1]
        upper = s[len(l) / 2]
        return float(lower + upper) / 2

def std_dev(a):

    n = len(a)
    if(n != 0):
        mean = sum(a) / n
        sd = sqrt(sum((x-mean)**2 for x in a) / n)
        return sd
    else:
        return 0

def plot_bar_chart(A_mean, A_std, B_mean, B_std):

    N = len(A_mean)
    ind = np.arange(N)+1   # the x locations for the groups
    width = 0.35       # the width of the bars: can also be len(x) sequence
    A_x = ind
    B_x = ind + width

    p1 = plt.bar(A_x, A_mean, width, color='r', yerr=A_std)
    p2 = plt.bar(B_x, B_mean, width, color='b', yerr=B_std)

    plt.ylabel('Delay')
    plt.title('Delay by file size and different loss rate')
    plt.xticks(ind+width, ('0.75KB', '7.5KB', '75KB', '750KB') )
    #plt.yticks(np.arange(0,11,1))
    plt.ylim([0, 30])
    plt.legend( (p1[0], p2[0]), ('1% link loss', '3% link loss'))

    plt.savefig(args.output)

if __name__=="__main__":

    data1 = open(args.input1)
    data2 = open(args.input2)
    lines1 = data1.readlines()
    lines2 = data2.readlines()
    A_mean = [None]*len(lines1)
    B_mean = [None]*len(lines1)
    A_std = [None]*len(lines1)
    B_std = [None]*len(lines1)

    for i in range(len(lines1)):
        line1 = lines1[i].split(' ')
        line1 = [float(x) for x in line1]
        line2 = lines2[i].split(' ')
        line2 = [float(x) for x in line2]

        Min = min(line1)
        std = std_dev(line1)
        w = [x for x in line1 if abs(x-Min) >= 2 * std]
        A_mean[i] = avg(w)
        A_std[i] = std_dev(w)

        Min = min(line2)
        std = std_dev(line2)
        w = [x for x in line2 if abs(x-Min) >= 2 * std]
        B_mean[i] = avg(w)
        B_std[i] = std_dev(w)


    plot_bar_chart(A_mean, A_std, B_mean, B_std)
