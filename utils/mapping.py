#!/usr/bin/env python

import folium
import numpy as np
from PIL import Image


def _lat_bounds(lat_grid, long_grid):
    bounds = [
        [
            lat_grid.min(),
            long_grid.min(),
        ],
        [
            lat_grid.max(),
            long_grid.max(),
        ]
    ]
    return bounds


def _cmap2rgb(step, cmap="gist_rainbow"):
    from matplotlib import cm
    return getattr(cm, cmap)(step, bytes=True)


def green_map_to_img(green_i):
    min_green = 0
    max_green = 0.7
    delta = (max_green-min_green)
    nx = green_i.shape[0]
    ny = green_i.shape[1]

    green_rgba = np.zeros(green_i.shape+(4,), dtype=np.uint8)
    for irow, row in enumerate(green_i):
        for icol, col in enumerate(row):
            step = int(256*(col-min_green)/delta)
            green_rgba[nx-irow-1][icol] = np.array(_cmap2rgb(step))
    return green_rgba


def create_map(green_i, lat_grid, long_grid):
    green_rgba = green_map_to_img(green_i)
    m = folium.Map(location=[52.299584, 4.971973], zoom_start=15)
    folium.raster_layers.ImageOverlay(
        green_rgba, opacity=0.5, mercator_project=True,
        bounds=_lat_bounds(lat_grid, long_grid)
    ).add_to(m)
    m.save('index.html')
