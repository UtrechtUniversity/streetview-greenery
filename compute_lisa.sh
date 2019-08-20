#!/bin/bash

N_JOBS=64

EXTRA_ARGS="-l 6"

if [ $# -ge 1 ]; then
    CFG_FILE=$1
    NEW_JOBS=(`grep 'N_JOBS_COMPUTE' $CFG_FILE`)
    if [ "${NEW_JOBS[*]}" != "" ]; then
        N_JOBS=${NEW_JOBS[1]}
    fi
    NEW_EXTRA_ARGS=(`grep 'EXTRA_ARGS' $CFG_FILE`)
    if [ "${NEW_EXTRA_ARGS[*]}" != "" ]; then
        EXTRA_ARGS=${NEW_EXTRA_ARGS[@]:1}
    fi
fi

COMMAND_FILE="temp_commands_compute.txt"
PRE_FILE="temp_pre_compute.txt"
CONFIG_FILE="compute_lisa.ini"

cat > $PRE_FILE << EOF_CAT 
#SBATCH -p gpu_shared
#SBATCH -n 3
cd `pwd`
source hpc/module_load_gpu.sh
EOF_CAT

rm -f $COMMAND_FILE

let "NJOB_MAX=N_JOBS-1"
for JOB in `seq 0 $NJOB_MAX`; do
    echo "\${python} ./streetgreen.py --bbox amsterdam_almere --njobs $N_JOBS --jobid $JOB --model deeplab-xception_71 --skip-overlay $EXTRA_ARGS" >> $COMMAND_FILE
done

batchgen -f $COMMAND_FILE $CONFIG_FILE -pre $PRE_FILE

sed -i '/#SBATCH --tasks-per-node=12/d' batch.slurm_lisa/sv_compute/batch*

rm -f $COMMAND_FILE $PRE_FILE
