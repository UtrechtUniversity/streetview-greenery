#!/usr/bin/env python
import sys

from utils.mapping import create_map
from utils.ndvi import tiff_to_overlay
from scipy import stats

if __name__ == "__main__":
    sound_overlay = tiff_to_overlay("./ndvi/noise2016_ad.tif", "sound",
                                    max_green=10)
#     stats.describe(sound_overlay.greenery)
#     green_overlay = tiff_to_overlay("./ndvi/ndvi_landsat8_2013_2017_ad.tif",
#                                     "remote sensing")
#     print(green_overlay.lat_grid)

    create_map([sound_overlay], html_file="sound.html")
