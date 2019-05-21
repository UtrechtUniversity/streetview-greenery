#!/usr/bin/env python

import os

from API import AdamPanoramaManager
from greenery import create_kriged_overlay
from utils.ndvi import tiff_to_overlay
from utils.mapping import create_map
from utils.selection import select_area


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

    overlay_fp = os.path.join(
        panoramas.data_dir, "krige_"+panoramas.id+".json"
    )
    krige_overlay = create_kriged_overlay(green_res, overlay_fp=overlay_fp)

    ndvi_tiff_fp = os.path.join("ndvi", "ndvi_landsat8_2013_2017_ad.tif")
    ndvi_overlay = tiff_to_overlay(ndvi_tiff_fp)

    map_fp = os.path.join(panoramas.id+".html")
    create_map([krige_overlay, ndvi_overlay], map_fp)


if __name__ == "__main__":
    main()
