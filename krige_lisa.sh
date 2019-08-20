#!/bin/bash

LVL=6
N_JOBS=16

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


declare -a CATEGORIES=(
    "road" "sidewalk" "building" 
    "wall" "fence" "pole" 
    "traffic light" "traffic sign" 
    "vegetation" "terrain" "sky" 
    "person" "rider" "car" 
    "truck" "bus" "train" 
    "motorcycle" "bicycle"
)

COMMAND_FILE="temp_commands.txt"
PRE_FILE="temp_pre.txt"
CONFIG_FILE="krige_lisa.ini"
rm -f $COMMAND_FILE

cat > $PRE_FILE << EOF_CAT
cd `pwd`
source hpc/module_load_cpu.sh
EOF_CAT

let "NJOB_MAX=N_JOBS-1"
CAT="vegetation"
for JOB in `seq 0 $NJOB_MAX`; do
    echo "\${python} ./streetgreen.py --bbox amsterdam_almere -g '$CAT' --model deeplab-xception_71 --njobs ${N_JOBS} --jobid $JOB" --parallel-krige $EXTRA_ARGS >> $COMMAND_FILE
done
# for CAT in "${CATEGORIES[@]}"; do
#     echo "\${python} ./streetgreen.py --bbox amsterdam_almere -l $LVL -g '$CAT' --model deeplab-xception_71" >> $COMMAND_FILE
# done

batchgen -f $COMMAND_FILE $CONFIG_FILE -pre $PRE_FILE

rm -f $COMMAND_FILE $PRE_FILE
