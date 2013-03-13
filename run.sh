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

mn -c

start=`date`
exptid=`date +%b%d-%H:%M`
plotpath=util
iperf=~/iperf-patched/src/iperf
dir=test_output_$exptid
iface=s1-eth2

python prr.py --bw-host 1000 \
              --bw-net 1.2 \
              --delay 25 \
              --dir $dir \
              --nflows 0 \
              --iperf $iperf \
              --loss 1 \
              --maxq 100 \
              --samples 100 \
              --index -1 \
              --time 600

python $plotpath/plot_queue.py -f $dir/qlen_$iface.txt -o $dir/q.png
for file in $dir/tcp_probe*.txt
do
  namelen=${#file}
  output_file=${file:0:${namelen}-4}.png
  python $plotpath/plot_tcpprobe.py -f file -o $dir/output_file
done
