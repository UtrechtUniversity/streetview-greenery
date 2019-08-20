#!/bin/bash

if [ $# -ge 1 ]; then
    CFG_FILE=$1
    CFG_NAME=`basename $CFG_FILE`
    CFG_ADD="_$CFG_NAME"
else
    CFG_FILE="__NONE__"
    CFG_ADD="_default"
fi

TMP_BATCH_FILE="batch_list.tmp"

function simulate_sbatch {
    N=$1
    for i in `seq $N`; do
        let "N_2=RANDOM"
        echo "Submitted batch job $N_2"
    done
}

function submit_layer {
    TYPE=$1
    CFG_FILE=$2
    CFG_ADD=$3
    if [ $# -ge 4 ]; then
        DEPENDENCIES=$4
        DEP_STR="afterok"
        for DEP in $DEPENDENCIES; do
            DEP_STR="$DEP_STR:$DEP"
        done
#         >&2 echo "$DEP_STR"
    fi
    
    if [ "$CFG_FILE" == "__NONE__" ]; then
        CFG_FILE=""
    fi
    
    JOB_LINE=`grep 'job_name = ' ${TYPE}_lisa.ini`
    if [ `uname -s` == "Darwin" ]; then
        sed -i '' -e "s/.*$JOB_LINE.*/job_name = sv_${TYPE}${CFG_ADD}/" ${TYPE}_lisa.ini
    else
        sed -i "s/.*$JOB_LINE.*/job_name = sv_${TYPE}${CFG_ADD}/" ${TYPE}_lisa.ini
    fi

    COMMAND=`./${TYPE}_lisa.sh $CFG_FILE`
    COMMAND=`echo "$COMMAND" | sed '/^*/d' | sed '/^$/d'`

    
    if [ "$DEP_STR" != "" ]; then
        COMMAND=`echo "$COMMAND" | sed 's/sbatch/sbatch --dependency='$DEP_STR'/'`
    fi
#     >&2 echo "$COMMAND"
    
#     COMMAND="simulate_sbatch 10"

    BATCH_NO=`eval "$COMMAND" | cut -f4 -d' '`
    echo "$BATCH_NO"
}


BATCH_NO=`submit_layer "prepare" "$CFG_FILE" "$CFG_ADD"`
echo "Submitted prepare job"
BATCH_NO=`submit_layer "compute" "$CFG_FILE" "$CFG_ADD" "$BATCH_NO"`
echo "Submitted compute job"
BATCH_NO=`submit_layer "krige" "$CFG_FILE" "$CFG_ADD" "$BATCH_NO"`
echo "Submitted krige job"
# echo $BATCH_NO
