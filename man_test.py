#!/usr/bin/env python

import os

from models import DeepLabModel
from greenery import VegetationPercentage
from API.tile_manager import TileManager
from greenery.visualization import plot_greenery
from utils.mapping import create_map
from utils.ndvi import tiff_to_overlay
from greenery import create_kriged_overlay


bbox = [
    [52.3588, 4.9145],
    [52.363, 4.931],
]

grid_level = 4
res_mult = 2

tile_man = TileManager(seg_model=DeepLabModel,
                       green_model=VegetationPercentage,
                       bbox=bbox, grid_level=grid_level,
                       n_job=2, job_id=1)
tile_man.get()
tile_man.load()
tile_man.seg_analysis()
green_res = tile_man.green_analysis()
resolution = tile_man.resolution()
resolution = [res_mult*x for x in resolution]
plot_greenery(green_res)

overlay = create_kriged_overlay(green_res, overlay_fp="oosterpark_tiled.json",
                                grid=resolution)

# ndvi_tiff_fp = os.path.join("ndvi", "ndvi_landsat8_2013_2017_ad.tif")
# ndvi_overlay = tiff_to_overlay(ndvi_tiff_fp)

create_map([overlay], "oosterpark_tiled.html")
