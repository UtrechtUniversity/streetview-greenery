#!/bin/bash

LVL=6

CATEGORIES=(
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

for CAT in ${CATEGORIES[*]}; do
    echo "\${python} ./streetgreen.py --bbox amsterdam_almere -l $LVL -g $CAT --model deeplab-xception_71" >> $COMMAND_FILE
done

batchgen -f $COMMAND_FILE $CONFIG_FILE -pre $PRE_FILE

rm -f $COMMAND_FILE $PRE_FILE
