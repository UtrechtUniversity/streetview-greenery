#!/usr/bin/env python

import os

from models import DeepLabModel
from greenery import VegetationPercentage, create_kriged_overlay
from API.tile_manager import AdamPanoramaTile
from greenery.visualization import plot_greenery
from utils.mapping import create_map
from utils.ndvi import tiff_to_overlay


def main():
    panoramas = AdamPanoramaTile(seg_model=DeepLabModel,
                                 green_model=VegetationPercentage,
                                 tile_name="oosterpark")
    nw = [52.363, 4.9145]
    se = [52.3588, 4.924]
    bbox = [nw, se]
    panoramas.get(bbox=bbox)
    panoramas.load(grid_level=5)
    panoramas.seg_analysis()
    green_res = panoramas.green_analysis()
    plot_greenery(green_res)

#     overlay = create_kriged_overlay(green_res, overlay_fp="oosterpark.json")

#     ndvi_tiff_fp = os.path.join("ndvi", "ndvi_landsat8_2013_2017_ad.tif")
#     ndvi_overlay = tiff_to_overlay(ndvi_tiff_fp)

#     create_map([overlay, ndvi_overlay], "oosterpark.html")


if __name__ == "__main__":
    main()
