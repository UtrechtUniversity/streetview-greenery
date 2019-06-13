#!/usr/bin/env python
'''
Created on 7 Jun 2019

@author: qubix
'''

from API import AdamPanorama
from models import DeepLabModel
import json
from greenery.greenery import ClassPercentage

data_dir = "test"
with open("test/meta_test.json") as f:
    meta_data = json.load(f)["meta_data"]

seg_model = DeepLabModel("mobilenet")
green_model = ClassPercentage("sky")

panorama = AdamPanorama(meta_data, data_dir=data_dir)
# panorama.seg_analysis(seg_model, show=False)
green_perc = panorama.green_analysis(seg_model, green_model)
# print(green_perc)
# print(panorama.all_seg_res)
