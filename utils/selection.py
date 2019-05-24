'''
Created on 16 May 2019

@author: qubix
'''

import sys

from models import DeepLabModel
from greenery import VegetationPercentage


def select_area(area, seg_model="mobilenet"):
    manager_kwargs = {
        'seg_model': DeepLabModel,
        'green_model': VegetationPercentage,
        'data_id': area,
        'seg_kwargs': {"model_name": seg_model}
    }
    get_kwargs = {}
    load_kwargs = {}

    if area == "adam_alm":
        load_kwargs['n_sample'] = 10000
    elif area == "mijndenhof":
        get_kwargs['center'] = [52.299584, 4.971973]
        get_kwargs['radius'] = 120
    elif area == "muiderpoort":
        get_kwargs['center'] = [52.360224, 4.935102]
        get_kwargs['radius'] = 400
    else:
        raise ValueError(f"Error: area '{area}' not defined.")
    return (manager_kwargs, get_kwargs, load_kwargs)


def select_bbox(area="amsterdam"):
    if area == "amsterdam":
        bbox = [
            [52.263, 4.686],
            [52.451, 5.041],
        ]
    elif area == "amsterdam_almere":
        bbox = [
            [52.240, 4.686],
            [52.445, 5.374],
        ]
    elif area == "almere":
        bbox = [
            [52.299, 5.079]
            [52.445, 5.374],
        ]
    elif area == "oosterpark":
        bbox = [
            [52.3588, 4.9145],
            [52.363, 4.931],
        ]
    elif area == "ouderkerk":
        bbox = [
            [52.284, 4.885],
            [52.306, 4.930],
        ]
    else:
        bbox_str = area.split(',')
        try:
            bbox = [
                [float(bbox_str[0]), float(bbox_str[1])],
                [float(bbox_str[2]), float(bbox_str[3])],
            ]
        except (ValueError, IndexError):
            print(f"Bad format/value for bounding box: {area}")
            sys.exit(123)

    return bbox


def select_seg_model(model_str="deeplab-mobilenet"):
    manager_kwargs = {}
    model_sub = model_str.split('-')
    if model_sub[0] == "deeplab":
        manager_kwargs['seg_model'] = DeepLabModel
    else:
        print(f"Unknown model: {model_sub[0]}/{model_str}")
        sys.exit(124)

    if len(model_sub) > 1:
        manager_kwargs['seg_kwargs'] = {'model_name': model_sub[1]}

    return manager_kwargs


def select_green_model(model_str="vegetation_perc"):
    if model_str == "vegetation_perc":
        manager_kwargs = {'green_model': VegetationPercentage}
    else:
        print(f"Unknown greenery measure {model_str}")
        sys.exit(125)
    return manager_kwargs
