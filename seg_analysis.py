#!/usr/bin/env python
'''
Script to run segmentation analysis on one picture with some 
implemented segmentation model.
'''

import os

# from models import DeepLabModel
from utils.selection import select_seg_model
from models.deeplab import plot_segmentation


def main():
    if len(os.sys.argv) <= 1:
        print("Error: need at least one argument -> picture to segment.")
    panorama_fp = os.sys.argv[1]
    seg_dict = {}
    if len(os.sys.argv) > 2:
        seg_dict['model_str'] = os.sys.argv[2]
    seg_dict = select_seg_model(**seg_dict)
    seg_model = seg_dict['seg_model']
    seg_kwargs = seg_dict['seg_kwargs']
    seg_instance = seg_model(**seg_kwargs)
    seg_res = seg_instance.run(panorama_fp)
    plot_segmentation(panorama_fp, **seg_res)


if __name__ == "__main__":
    main()
