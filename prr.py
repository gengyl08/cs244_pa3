#!/usr/bin/python

##################################################
#CS244 Assignment 3: Proportional Rate Reduction #
#Team members: Yilong Geng & Bo Wang             #
##################################################


from mininet.topo import Topo
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.net import Mininet
from mininet.log import lg
from mininet.util import dumpNodeConnections

import subprocess
from subprocess import Popen, PIPE
from time import sleep, time
from multiprocessing import Process
#import termcolor as T
from argparse import ArgumentParser

import sys
import os
from util.monitor import monitor_qlen
from util.helper import stdev

import re
import matplotlib.pyplot as plt

# Parse arguments

parser = ArgumentParser(description="Buffer sizing tests")
parser.add_argument('--bw-host', '-B',
                    dest="bw_host",
                    type=float,
                    action="store",
                    help="Bandwidth of host links",
                    required=True)

parser.add_argument('--bw-net', '-b',
                    dest="bw_net",
                    type=float,
                    action="store",
                    help="Bandwidth of network link",
                    required=True)

parser.add_argument('--delay',
                    dest="delay",
                    type=float,
                    help="Delay in milliseconds of host links",
                    default=87)

parser.add_argument('--dir', '-d',
                    dest="dir",
                    action="store",
                    help="Directory to store outputs",
                    default="results",
                    required=True)

parser.add_argument('--maxq',
                    dest="maxq",
                    action="store",
                    help="Max buffer size of network interface in packets",
                    default=1000)

parser.add_argument('--cong',
                    dest="cong",
                    help="Congestion control algorithm to use",
                    default="reno")

parser.add_argument('--loss',
                    dest="loss",
                    help="Link loss rate",
                    default=0)

parser.add_argument('--samples',
                    dest="samples",
                    help="Number of samples",
                    default=20)

parser.add_argument('--index',
                    dest="index",
                    help="Which file to fetch",
                    default="10")

parser.add_argument('--time',
                    dest="time",
                    help="Time to run",
                    default="200")

# Parse Arguments
args = parser.parse_args()

# Build directory for results
if not os.path.exists(args.dir):
    os.makedirs(args.dir)

lg.setLogLevel('info')

# Server-Client topology to be instantiated in Mininet
class SCTopo(Topo):

    def __init__(self, bw_host=None, bw_net=None,
                 delay=None, maxq=None):
        # Add default members to class.
        super(SCTopo, self ).__init__()
        self.bw_host = bw_host
        self.bw_net = bw_net
        self.delay = delay
        self.maxq = maxq
        self.create_topology()

    def create_topology(self):
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        s1 = self.addSwitch('s1')

        self.addLink(h1, s1, bw=self.bw_host, delay=self.delay, max_queue_size=int(self.maxq), loss=float(args.loss), htb=True)
        self.addLink(h2, s1, bw=self.bw_net, delay=self.delay, max_queue_size=int(self.maxq), loss=float(args.loss), htb=True)

def start_tcpprobe(output, port):
    "Install tcp_probe module and dump to file"
    os.system("rmmod tcp_probe 2>/dev/null; modprobe tcp_probe port=%d full=1;" % port)
    Popen("cat /proc/net/tcpprobe > %s/%s 2>/dev/null" %
          (args.dir, output), shell=True)

def stop_tcpprobe():
    os.system("killall -q -9 cat &>/dev/null; rmmod tcp_probe &>/dev/null;")

def start_measure(iface, net):

    print "Starting measurements."

    ret = [None]*4
    temp = [None]*int(args.samples);
    h1 = net.getNodeByName('h1')
    h2 = net.getNodeByName('h2')
    IP1 = h1.IP()
    IP2 = h2.IP()

    #Fetch files of all length
    if (args.index == "-1"):
        result = open("%s/result_loss%s.txt" % (args.dir, args.loss), 'w')
        for i in range(4):
            print "================================"
            print "Fetching index" + str(i+1) + ".html"
            for j in range(int(args.samples)):
                #start_tcpprobe("tcp_probe_index%d_%d.txt" % (i+1, j+1), 80)
                line = h2.popen("curl -o /dev/null -s -w %%\{time_total\} %s/http/index%s.html" % (IP1, i+1), shell=True).stdout.readline()
                temp[j] = line
                print "Fetch index%d.html %d: finish in %s seconds." % (i+1, j+1, line)
                #stop_tcpprobe()
            result.write(' '.join(temp)+'\n')
        result.close()
    #Generate a long flow
    elif(args.index == "0"):
        start_tcpprobe("tcp_probe.txt", 0)
        h1.popen("iperf -c %s -t %s -yc -Z %s > %s/%s" % (IP2, args.time, args.cong, args.dir, "iperf_client.txt")).wait()
        stop_tcpprobe()
    #Fetch a file of certain length
    else:
        result = open("%s/result_loss%s_index%s.txt" % (args.dir, args.loss, args.index), 'w')
        print "================================"
        print "Fetching index" + args.index + ".html"
        for j in range(int(args.samples)):
            start_tcpprobe("tcp_probe_index%d_%d.txt" % (int(args.index), j+1), 80)
            line = h2.popen("curl -o /dev/null -s -w %%\{time_total\} %s/http/index%s.html" % (IP1, args.index), shell=True).stdout.readline()
            temp[j] = line
            print "Finish in " + line + " seconds."
            stop_tcpprobe()
        result.write(' '.join(temp)+'\n')
        result.close()

    return

def start_receiver(net):
    print "Starting receiver."
    h2 = net.getNodeByName('h2')
    h2.popen("iperf -s > %s/iperf_server.txt" % args.dir, shell=True)
        
def start_webserver(net):
    print "Starting web server."
    h1 = net.getNodeByName('h1')
    proc = h1.popen("python http/webserver.py", shell=True)
    sleep(1)
    return [proc]

def main():

    topo = SCTopo(bw_host=args.bw_host,
                    delay='%sms' % args.delay,
                    bw_net=args.bw_net, maxq=args.maxq)
    net = Mininet(topo=topo, host=CPULimitedHost, link=TCLink)
    net.start()
    dumpNodeConnections(net.hosts)

    start_receiver(net)

    start_webserver(net)

    start_measure(iface='s1-eth2', net=net)

    # Shut down iperf processes
    os.system('killall -9 iperf')

    net.stop()

    Popen("killall -9 top bwm-ng tcpdump cat mnexec", shell=True).wait()

if __name__ == '__main__':
    try:
        main()
    except:
        print "-"*80
        print "Caught exception.  Cleaning up..."
        print "-"*80
        import traceback
        traceback.print_exc()
        os.system("killall -9 top bwm-ng tcpdump cat mnexec iperf; mn -c")

