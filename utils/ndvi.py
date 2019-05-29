#!/usr/bin/env python
import sys

import numpy as np
from osgeo import gdal, osr

from utils.mapping import create_map, MapImageOverlay


def tiff_to_overlay(tiff_fp, name=None, min_green=-0.03, max_green=None):
    if name is None:
        name = tiff_fp
    ds = gdal.Open(tiff_fp)
    prj = ds.GetProjection()
    srs = osr.SpatialReference(wkt=prj)
    warped_ds = gdal.Warp('', ds, dstSRS='EPSG:4326', format='VRT')
    warped_array = np.array(warped_ds.GetRasterBand(1).ReadAsArray())
    warped_array = np.flip(warped_array, axis=0)

    ulx, xres, _, uly, _, yres = warped_ds.GetGeoTransform()
    lrx = ulx + (warped_ds.RasterXSize * xres)
    lry = uly + (warped_ds.RasterYSize * yres)

    lat_grid = np.flip(np.linspace(uly, lry, warped_ds.RasterYSize))
    long_grid = np.linspace(ulx, lrx, warped_ds.RasterXSize)

#     min_green = warped_array[np.where(warped_array > -1)].min()
    if max_green is None:
        max_green = warped_array.max()+0.05

    overlay = MapImageOverlay(warped_array, lat_grid=lat_grid,
                              long_grid=long_grid,
                              min_green=min_green, name=name,
                              max_green=max_green,
                              cmap='Greys')
    return overlay
#     create_map(warped_array, , html_file="ndvi.html",
#                min_green=min_green, max_green=)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Need one argument: tiff filename")
        sys.exit()
    print(f"Reading {sys.argv[1]}")
    print(tiff_to_overlay(sys.argv[1]))
