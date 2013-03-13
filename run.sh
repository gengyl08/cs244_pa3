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

exptid=`date +%m%d%H%M`
plotpath=util
iperf=~/iperf-patched/src/iperf
dir=test_output_$exptid
iface=s1-eth2

for loss in 1 3; do
    python prr.py --bw-host 1000 \
                  --bw-net 1.2 \
                  --delay 25 \
                  --dir $dir \
                  --maxq 100 \
                  --loss $loss \
                  --samples 10 \
                  --index -1
done

python prr.py --bw-host 1000 \
              --bw-net 1.2 \
              --delay 25 \
              --dir $dir \
              --maxq 50 \
              --index 0 \
              --time 20

#Plot cwnd
for input_file in $dir/tcp_probe*.txt
do
  namelen=${#input_file}
  output_file=${input_file:0:${namelen}-4}.png
  python parse_cwnd.py --input $input_file --output $output_file
done

#plot delay
for input_file in $dir/result*.txt
do
  namelen=${#input_file}
  output_file=${input_file:0:${namelen}-4}.png
  python delay_analysis.py --file $input_file --output $output_file
done
