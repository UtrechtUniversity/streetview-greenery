#!/bin/bash

declare -a CATEGORIES=(
    "road" "sidewalk" "building" 
    "wall" "fence" "pole" 
    "traffic light" "traffic sign" 
    "vegetation" "terrain" "sky" 
    "person" "rider" "car" 
    "truck" "bus" "train" 
    "motorcycle" "bicycle"
)

for CAT in "${CATEGORIES[@]}"; do
    ./streetgreen.py --bbox amsterdam_almere -g "$CAT" --model deeplab-xception_71 -l 6
done
