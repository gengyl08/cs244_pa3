#!/bin/bash

# Exit on any failure
set -e

# Check for uninitialized variables
set -o nounset

ctrlc() {
	killall -9 python
	mn -c
	exit
}

trap ctrlc SIGINT

start=`date`
exptid=`date +%b%d-%H:%M`

rootdir=buffersizing-$exptid
plotpath=util
iperf=~/iperf-patched/src/iperf
dir=test_output_$(uname -r)
iface=s1-eth2

mn -c

python buffersizing.py --bw-host 1000 \
		--bw-net 10 \
		--delay 100 \
		--dir $dir \
		--nflows 0 \
		--iperf $iperf \
                --loss 0 \
                --maxq 100 \
                --samples 200 \
                --index 0 \
                --time 600

python $plotpath/plot_queue.py -f $dir/qlen_$iface.txt -o $dir/q.png
python $plotpath/plot_tcpprobe.py -f $dir/tcp_probe.txt -o $dir/cwnd.png
