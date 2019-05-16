'''
Created on 16 May 2019

@author: qubix
'''

from models import DeepLabModel
from greenery.segment_perc import VegetationPercentage


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
