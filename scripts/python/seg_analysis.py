#!/usr/bin/env python
'''
Script to run segmentation analysis on one picture with some 
implemented segmentation model.
'''

import os

# from models import DeepLabModel
from greenstreet.utils.selection import get_segmentation_model
from greenstreet.models.deeplab import plot_segmentation


def main():
    if len(os.sys.argv) <= 1:
        print("Error: need at least one argument -> picture to segment.")
    panorama_fp = os.sys.argv[1]
    model_type = "deeplab-mobilenet"
    if len(os.sys.argv) > 2:
        model_type = os.sys.argv[2]
#     seg_dict = select_seg_model(**seg_dict)
#     seg_model = seg_dict['seg_model']
#     seg_kwargs = seg_dict['seg_kwargs']
#     seg_instance = seg_model(**seg_kwargs)
    seg_model = get_segmentation_model(model_type)
    seg_res = seg_model.run(panorama_fp)
    print(seg_res)
    plot_segmentation(panorama_fp, **seg_res)


if __name__ == "__main__":
    main()
