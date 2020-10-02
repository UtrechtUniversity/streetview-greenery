#!/bin/bash

# First install tensorflow-gpu with pip:
# pip install --user tensorflow-gpu=1.12.2

module unload GCCcore
module unload binutils
module load cuDNN/7.3.1-CUDA-9.0.176
module load CUDA/9.0.176
module load gdal
