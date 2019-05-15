#!/usr/bin/env python

import os

from API import AdamPanoramaManager
from models import DeepLabModel
from greenery.segment_perc import VegetationPercentage, plot_greenery,\
    plot_green_krige
from utils.ndvi import tiff_to_overlay
from utils.mapping import create_map


def select_area(area):
    manager_kwargs = {
        'seg_model': DeepLabModel,
        'green_model': VegetationPercentage,
        'data_id': area,
    }
    get_kwargs = {}
    load_kwargs = {}

    if area == "adam_alm":
        load_kwargs['n_sample'] = 10000
    elif area == "mijndenhof":
        get_kwargs['center'] = [52.299584, 4.971973]
        get_kwargs['radius'] = 150
    elif area == "muiderpoort":
        get_kwargs['center'] = [52.360224, 4.935102]
        get_kwargs['radius'] = 400
    else:
        raise ValueError(f"Error: area '{area}' not defined.")
    return (manager_kwargs, get_kwargs, load_kwargs)


def main():
    area = "muiderpoort"
    if len(os.sys.argv) > 1:
        area = os.sys.argv[1]

    manager_kwargs, get_kwargs, load_kwargs = select_area(area)
    # Start up the panorama manager.
    panoramas = AdamPanoramaManager(**manager_kwargs)
    # Get the meta data for the panoramas.
    panoramas.get(**get_kwargs)
    # Load panoramas into memory (from file or internet).
    panoramas.load(**load_kwargs)

    # Do segmentation analysis for loaded panorama's.
    panoramas.seg_analysis()
    # Get greenery from segmentation analysis.
    green_res = panoramas.green_analysis()
    # Plot the kriged map of the greenery.

    overlay_fp = os.path.join(panoramas.data_dir, "krige_"+panoramas.id+".json")
    krige_overlay = plot_green_krige(green_res, overlay_fp=overlay_fp)

    ndvi_tiff_fp = os.path.join("ndvi", "ndvi_landsat8_2013_2017_ad.tif")
    ndvi_overlay = tiff_to_overlay(ndvi_tiff_fp)

    map_fp = os.path.join("doc", panoramas.id+".html")
    create_map([krige_overlay, ndvi_overlay], map_fp)


if __name__ == "__main__":
    main()
