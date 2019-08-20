#!/bin/bash

N_JOBS=8

EXTRA_ARGS="-l 6"

if [ $# -ge 1 ]; then
    CFG_FILE=$1
    NEW_JOBS=(`grep 'N_JOBS_PREPARE' $CFG_FILE`)
    if [ "${NEW_JOBS[*]}" != "" ]; then
        N_JOBS=${NEW_JOBS[1]}
    fi
    NEW_EXTRA_ARGS=(`grep 'EXTRA_ARGS' $CFG_FILE`)
    if [ "${NEW_EXTRA_ARGS[*]}" != "" ]; then
        EXTRA_ARGS=${NEW_EXTRA_ARGS[@]:1}
    fi
fi

echo "$N_JOBS $EXTRA_ARGS"
COMMAND_FILE="temp_commands.txt"
PRE_FILE="temp_pre.txt"
CONFIG_FILE="prepare_lisa.ini"

cat > $PRE_FILE << EOF_CAT
cd `pwd`
source hpc/module_load_cpu.sh
EOF_CAT

rm -f $COMMAND_FILE

let "NJOB_MAX=N_JOBS-1"
for JOB in `seq 0 $NJOB_MAX`; do
    echo "\${python} ./streetgreen.py --prepare --bbox amsterdam_almere --njobs $N_JOBS --jobid $JOB $EXTRA_ARGS" >> $COMMAND_FILE
done

batchgen -f $COMMAND_FILE $CONFIG_FILE -pre $PRE_FILE

rm -f $COMMAND_FILE $PRE_FILE
