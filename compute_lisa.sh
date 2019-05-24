#!/bin/bash

N_JOBS=1
if [ $# -ge 1 ]; then
    N_JOBS=$1
fi

COMMAND_FILE="temp_commands_compute.txt"
PRE_FILE="temp_pre_compute.txt"
CONFIG_FILE="compute_lisa.ini"

cat > $PRE_FILE << EOF_CAT 
#SBATCH -p gpu_shared
#SBATCH -n 3
cd `pwd`
source hpc/module_load.sh
EOF_CAT

rm -f $COMMAND_FILE

let "NJOB_MAX=N_JOBS-1"
for JOB in `seq 0 $NJOB_MAX`; do
    echo "\${python} ./streetgreen amsterdam_almere --njobs $N_JOBS --jobid $JOB --model deeplab-xception_71 -l 2" >> $COMMAND_FILE
done

cat $PRE_FILE

batchgen -f $COMMAND_FILE $CONFIG_FILE -pre $PRE_FILE

rm -f $COMMAND_FILE $PRE_FILE
