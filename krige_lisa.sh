#!/bin/bash

LVL=6
N_JOBS=16

EXTRA_ARGS="-l 6"
CLASSES=("vegetation")

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
    NEW_CLASSES=(`grep 'KRIGE_CLASSES' $CFG_FILE`)
    if [ "${NEW_CLASSES[*]}" != "" ]; then
        CLASSES=${NEW_CLASSES[@]:1}
    fi
    echo ${CLASSES[*]}
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

function valid_cat {
    NEW_CAT=$1
    for CAT in ${CATEGORIES[*]}; do
        if [ "$CAT" == "$NEW_CAT" ]; then
            return 0
        fi
    done
    return 1
}

if [ "${CLASSES[0]}"  == "all" ]; then
    CLASSES=( ${CATEGORIES[*]} )
else
    for CAT in ${CLASSES[*]}; do
        if ! valid_cat $CAT; then
            echo "Error: $CAT is not a valid category (in config file)."
            return 129
        fi
    done
fi
        


COMMAND_FILE="temp_commands.txt"
PRE_FILE="temp_pre.txt"
CONFIG_FILE="krige_lisa.ini"
rm -f $COMMAND_FILE

cat > $PRE_FILE << EOF_CAT
cd `pwd`
source hpc/module_load_cpu.sh
EOF_CAT

let "NJOB_MAX=N_JOBS-1"



for CAT in ${CLASSES[*]}; do
    for JOB in `seq 0 $NJOB_MAX`; do
        echo "\${python} ./streetgreen.py --bbox amsterdam_almere -g '$CAT' --model deeplab-xception_71 --njobs ${N_JOBS} --jobid $JOB" --parallel-krige $EXTRA_ARGS >> $COMMAND_FILE
    done
done


batchgen -f $COMMAND_FILE $CONFIG_FILE -pre $PRE_FILE

rm -f $COMMAND_FILE $PRE_FILE
