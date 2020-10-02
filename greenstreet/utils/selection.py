
import sys

from greenstreet.models import DeepLabModel
from greenstreet.greenery.greenery import GreeneryUnweighted, CubicWeighted,\
    PanoramaWeighted
from greenstreet.API.adam.panorama_job import AdamPanoramaJob
from greenstreet.API.adam.cubic_job import AdamCubicJob


def select_area(area, seg_model="mobilenet"):
    manager_kwargs = {
        'seg_model': DeepLabModel,
        'green_model': GreeneryUnweighted,
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
            [52.299, 5.079],
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
    elif area == "gaasperdam":
        bbox = [
            [52.292, 4.960],
            [52.305, 5.000],
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


def get_segmentation_model(model_type="deeplab-mobilenet", **kwargs):
    model_sub = model_type.split('-')
    if model_sub[0] == "deeplab":
        model_class = DeepLabModel
    else:
        raise ValueError(f"Unknown model: {model_sub[0]}/{model_type}")

    extra_kwargs = {}
    if len(model_sub) > 1:
        extra_kwargs = {'model_name': model_sub[1]}

    return model_class(**kwargs, **extra_kwargs)


def get_green_model(use_panorama=True, weighted_panorama=True):
    if not weighted_panorama:
        return GreeneryUnweighted()
    if use_panorama:
        return PanoramaWeighted()
    return CubicWeighted()


def get_job_runner(use_panorama, seg_model, green_model):
    if use_panorama:
        return AdamPanoramaJob(seg_model, green_model)
    return AdamCubicJob(seg_model, green_model)
