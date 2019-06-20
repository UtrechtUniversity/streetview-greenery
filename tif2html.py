#!/usr/bin/env python
import sys

from utils.mapping import create_map
from utils.ndvi import tiff_to_overlay
from scipy import stats

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_fp = sys.argv[1]
        title = "greenery"
        max_green = 1
    else:
        file_fp = "./ndvi/noise2016_ad.tif"
        title = "sound"
        max_green = 10
    html_fp = title+".html"
    overlay = tiff_to_overlay(file_fp, title, max_green=max_green)
#     stats.describe(sound_overlay.greenery)
#     green_overlay = tiff_to_overlay("./ndvi/ndvi_landsat8_2013_2017_ad.tif",
#                                     "remote sensing")
#     print(green_overlay.lat_grid)

    create_map([overlay], html_file=html_fp)
