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

mn -c

python buffersizing.py --bw-host 1000 \
		--bw-net 62.5 \
		--delay 43.5 \
		--dir test_output \
		--nflows 100 \
		--iperf $iperf
