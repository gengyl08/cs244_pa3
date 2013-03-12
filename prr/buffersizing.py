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

parser.add_argument('--nflows',
                    dest="nflows",
                    action="store",
                    type=int,
                    help="Number of long iperf flows",
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

parser.add_argument('--iperf',
                    dest="iperf",
                    help="Path to custom iperf",
                    required=True)

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

# Path of custom iperf
CUSTOM_IPERF_PATH = args.iperf
assert(os.path.exists(CUSTOM_IPERF_PATH))

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

def start_tcpprobe():
    "Install tcp_probe module and dump to file"
    print "Starting TCP Probe."
    os.system("rmmod tcp_probe 2>/dev/null; modprobe tcp_probe;")
    Popen("cat /proc/net/tcpprobe > %s/tcp_probe.txt" %
          args.dir, shell=True)

def stop_tcpprobe():
    print "Stopping TCP Probe."
    os.system("killall -9 cat; rmmod tcp_probe &>/dev/null;")

def count_connections():
    "Count current connections in iperf output file"
    out = args.dir + "/iperf_server.txt"
    lines = Popen("grep connected %s | wc -l" % out,
                  shell=True, stdout=PIPE).communicate()[0]
    return int(lines)

def set_q(iface, q):
    "Change queue size limit of interface"
    cmd = ("tc qdisc change dev %s parent 1:1 "
           "handle 10: netem limit %s" % (iface, q))
    subprocess.check_output(cmd, shell=True)

def set_speed(iface, spd):
    "Change htb maximum rate for interface"
    cmd = ("tc class change dev %s parent 1:0 classid 1:1 "
           "htb rate %s burst 15k" % (iface, spd))
    os.system(cmd)

def get_txbytes(iface):
    f = open('/proc/net/dev', 'r')
    lines = f.readlines()
    for line in lines:
        if iface in line:
            break
    f.close()
    if not line:
        raise Exception("could not find iface %s in /proc/net/dev:%s" %
                        (iface, lines))
    # Extract TX bytes from:
    #Inter-|   Receive                                                |  Transmit
    # face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    # lo: 6175728   53444    0    0    0     0          0         0  6175728   53444    0    0    0     0       0          0
    return float(line.split()[9])

def get_rates(iface):
    nsamples = 4
    last_time = 0
    last_txbytes = 0
    ret = []
    sleep(3)
    while nsamples:
        nsamples -= 1
        txbytes = get_txbytes(iface)
        now = time()
        elapsed = now - last_time
        last_time = now
        # Get rate in Mbps; correct for elapsed time.
        rate = (txbytes - last_txbytes) * 8.0 / 1e6 / elapsed
        if last_txbytes != 0:
            ret.append(rate)
        last_txbytes = txbytes
        print '.',
        sys.stdout.flush()
        sleep(1)
    return avg(ret)

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

def start_measure(iface, net):

    print "Starting measurements."

    print "--Establishing long flow connectinos."
    # Set a higher speed on the bottleneck link in the beginning so
    # flows quickly connect
    set_speed(iface, "2Gbit")

    succeeded = 0
    wait_time = 300
    while wait_time > 0 and succeeded != args.nflows:
        wait_time -= 1
        succeeded = count_connections()
        print 'Connections %d/%d succeeded\r' % (succeeded, args.nflows)
        sys.stdout.flush()
        sleep(1)

    monitor = Process(target=monitor_qlen,
                      args=(iface, 0.01, '%s/qlen_%s.txt' %
                            (args.dir, iface)))
    monitor.start()

    if succeeded != args.nflows:
        print 'Giving up'
        return -1

    # TODO: Set the speed back to the bottleneck link speed.
    set_speed(iface, "%.2fMbit" % args.bw_net)
    sys.stdout.flush()

    print "--Wait till link utilization become stable."
    rate = 10
    rate_new = 0
    while(abs(rate-rate_new) > 0.1 * args.bw_net):
        rate = rate_new
        rate_new = get_rates(iface)
        print rate_new

    print "--Starting tests."   
    ret = [None]*9
    temp = [None]*int(args.samples);
    h1 = net.getNodeByName('h1')
    h2 = net.getNodeByName('h2')
    IP1 = h1.IP()
    IP2 = h2.IP()

    #Fetch files of all length
    if (args.index == "10"):
        result = open("%s/result_%s_%s.txt" % (args.dir, args.nflows, args.loss), 'w')
        #h1.popen("%s -c %s -n 2M -yc -Z %s > %s/%s" % (CUSTOM_IPERF_PATH, IP2, args.cong, args.dir, "iperf_client.txt")).wait()
        for i in range(9):
            print "================================"
            print "Fetching index" + str(i+1) + ".html"
            for j in range(int(args.samples)):
                line = h2.popen("curl -o /dev/null -s -w %%\{time_total\} %s/http/index%s.html" % (IP1, i+1), shell=True).stdout.readline()
                temp[j] = line
                print "Finish in " + line + " seconds."
            result.write(' '.join(temp)+'\n')
        result.close()
    elif(args.index == "0"):
        h1.popen("%s -c %s -t %s -yc -Z %s > %s/%s" % (CUSTOM_IPERF_PATH, IP2, args.time, args.cong, args.dir, "iperf_client.txt")).wait()

    #Fetch a file of certain length
    else:
        result = open("%s/result_%s_%s_index%s.txt" % (args.dir, args.nflows, args.loss, args.index), 'w')
        print "================================"
        print "Fetching index" + args.index + ".html"
        for j in range(int(args.samples)):
            line = h2.popen("curl -o /dev/null -s -w %%\{time_total\} %s/http/index%s.html" % (IP1, args.index), shell=True).stdout.readline()
            temp[j] = line
            print "Finish in " + line + " seconds."
        result.write(' '.join(temp)+'\n')
        result.close()

    monitor.terminate()
    return

def start_receiver(net):
    print "Starting receiver."
    h2 = net.getNodeByName('h2')
    h2.popen("%s -s > %s/iperf_server.txt" % (CUSTOM_IPERF_PATH, args.dir), shell=True)

def start_sender(net):
    print "Starting senders."
    # Seconds to run iperf; keep this very high
    seconds = 3600
    h1 = net.getNodeByName('h1')
    h2 = net.getNodeByName('h2')
    IP2 = h2.IP()
    for i in range(args.nflows):
        h1.popen("%s -c %s -t %d -i 1 -yc -Z %s > %s/%s" % (CUSTOM_IPERF_PATH, IP2, seconds, args.cong, args.dir, "iperf_client_"+str(i)+".txt"))
        
def start_webserver(net):
    print "Starting web server."
    h1 = net.getNodeByName('h1')
    proc = h1.popen("python http/webserver.py", shell=True)
    sleep(1)
    return [proc]

def plot():
    result = open("%s/result_%s_%s.txt" % (args.dir, args.nflows, args.loss), 'r')
    lines = result.readlines()
    y = [None]*len(lines)
    for i in range(len(lines)):
        line = lines[i]
        line = line.split(' ')
        line = [float(x) for x in line]
        y[i] = avg(line)
    plt.plot(range(len(y)), y)
    plt.savefig("%s/fig_%s_%s.png" % (args.dir, args.nflows, args.loss))

def main():

    start = time()
    # Reset to known state
    topo = SCTopo(bw_host=args.bw_host,
                    delay='%sms' % args.delay,
                    bw_net=args.bw_net, maxq=args.maxq)
    net = Mininet(topo=topo, host=CPULimitedHost, link=TCLink)
    net.start()
    dumpNodeConnections(net.hosts)
    net.pingAll()

    start_receiver(net)

    start_tcpprobe()

    start_sender(net)

    start_webserver(net)

    start_measure(iface='s1-eth2', net=net)

    plot()

    

    # Shut down iperf processes
    os.system('killall -9 ' + CUSTOM_IPERF_PATH)
    net.stop()
    Popen("killall -9 top bwm-ng tcpdump cat mnexec", shell=True).wait()
    stop_tcpprobe()
    end = time()

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

