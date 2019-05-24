#!/bin/bash

N_JOBS=1
if [ $# -ge 1 ]; then
    N_JOBS=$1
fi

COMMAND_FILE="temp_commands.txt"
PRE_FILE="temp_pre.txt"
CONFIG_FILE="prepare_lisa.ini"
echo "cd `pwd`" > $PRE_FILE

rm -f $COMMAND_FILE

let "NJOB_MAX=N_JOBS-1"
for JOB in `seq 0 $NJOB_MAX`; do
    echo "\${python} ./streetgreen --prepare amsterdam_almere --njobs $N_JOBS --jobid $JOB -l 2" >> $COMMAND_FILE
done

cat $COMMAND_FILE

batchgen -f $COMMAND_FILE $CONFIG_FILE -pre $PRE_FILE

rm -f $COMMAND_FILE $PRE_FILE
