#!/bin/bash

LVL=6
N_JOBS=16

EXTRA_ARGS="-l 6"
CLASSES=("vegetation")

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
    local NEW_CAT=$1
    for LOC_CAT in "${CATEGORIES[@]}"; do
        if [ "$LOC_CAT" == "$NEW_CAT" ]; then
            return 0
        fi
    done
    return 1
}

function parse_classes {
    local N_INVALID=0
    local FIRST_INVALID=""
    local NEW_CLASS=""
    
    
    if [ "${NEW_CLASSES[1]}" == "all" ]; then
        CLASSES=( "${CATEGORIES[@]}" )
        return
    fi

    CLASSES=()
    
    for CLASS in ${NEW_CLASSES[@]:1}; do        
        if [ "$N_INVALID" != "0" ]; then
            if valid_cat "$FIRST_INVALID $CLASS"; then
                NEW_CLASS="$FIRST_INVALID $CLASS"
                N_INVALID="0"
            else
                echo "Error: class is invalid: $FIRST_INVALID / '$FIRST_INVALID $CLASS'"
                exit 192
            fi
        else
            if ! valid_cat "$CLASS"; then
                FIRST_INVALID="$CLASS"
                N_INVALID="1"
                continue
            else
                NEW_CLASS="$CLASS"
            fi
        fi
        CLASSES+=("$NEW_CLASS")
    done
    if [ "$N_INVALID" != "0" ]; then
        echo "Error: class is invalid: $FIRST_INVALID"
        exit 192
    fi
}

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
    NEW_CLASSES=(`grep 'KRIGE_CLASSES' $CFG_FILE | tr '[:upper:]' '[:lower:]'`)
    parse_classes
#     if [ "${NEW_CLASSES[*]}" != "" ]; then
#         CLASSES=${NEW_CLASSES[@]:1}
#     fi
fi

# exit 0


# if [ "${CLASSES[0]}"  == "all" ]; then
# else
#     for CAT in ${CLASSES[*]}; do
#         if ! valid_cat "$CAT"; then
#             echo "Error: $CAT is not a valid category (in config file)."
#             exit 129
#         fi
#     done
# fi



COMMAND_FILE="temp_commands.txt"
PRE_FILE="temp_pre.txt"
CONFIG_FILE="krige_lisa.ini"
rm -f $COMMAND_FILE

cat > $PRE_FILE << EOF_CAT
cd `pwd`
source hpc/module_load_cpu.sh
EOF_CAT

let "NJOB_MAX=N_JOBS-1"



for CAT in "${CLASSES[@]}"; do
    for JOB in `seq 0 $NJOB_MAX`; do
        echo "\${python} ./streetgreen.py --bbox amsterdam_almere -g '$CAT' --model deeplab-xception_71 --njobs ${N_JOBS} --jobid $JOB" --parallel-krige $EXTRA_ARGS >> $COMMAND_FILE
    done
done


batchgen -f $COMMAND_FILE $CONFIG_FILE -pre $PRE_FILE

rm -f $COMMAND_FILE $PRE_FILE
