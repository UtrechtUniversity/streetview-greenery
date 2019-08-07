#!/bin/bash

LVL=6
N_JOBS=16

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
    echo "\${python} ./streetgreen.py --bbox amsterdam_almere -l $LVL -g '$CAT' --model deeplab-xception_71 --njobs ${N_JOBS} --jobid $JOB" >> $COMMAND_FILE
done
# for CAT in "${CATEGORIES[@]}"; do
#     echo "\${python} ./streetgreen.py --bbox amsterdam_almere -l $LVL -g '$CAT' --model deeplab-xception_71" >> $COMMAND_FILE
# done

batchgen -f $COMMAND_FILE $CONFIG_FILE -pre $PRE_FILE

rm -f $COMMAND_FILE $PRE_FILE
