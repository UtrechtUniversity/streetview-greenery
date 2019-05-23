#!/usr/bin/env python

import folium
import numpy as np
from PIL import Image
import json
from json.decoder import JSONDecodeError


class MapImageOverlay:
    "Overlay that can be plotted over a street map. Assumes WGS 84."
    def __init__(self, greenery, alpha_map=None, lat_grid=None, long_grid=None,
                 min_green=0.0, max_green=0.7, cmap="gist_rainbow", name=None):
        if isinstance(greenery, str):
            self.load(greenery)
        else:
            self.greenery = greenery
            self.alpha_map = alpha_map
            self.lat_grid = lat_grid
            self.long_grid = long_grid
            self.min_green = min_green
            self.max_green = max_green
            self.cmap = cmap
            self.name = name

    def load(self, file_fp):
        try:
            with open(file_fp, "r") as f:
                gr_dict = json.load(f)
        except JSONDecodeError:
            raise FileNotFoundError("Error reading file {file_fp}")
        self.greenery = np.array(gr_dict['greenery'])
        if 'alpha_map' in gr_dict:
            self.alpha_map = np.array(gr_dict['alpha_map'])
        else:
            self.alpha_map = None
        self.lat_grid = np.array(gr_dict['lat_grid'])
        self.long_grid = np.array(gr_dict['long_grid'])
        self.min_green = gr_dict['min_green']
        self.max_green = gr_dict['max_green']
        self.cmap = gr_dict['cmap']
        self.name = gr_dict['name']

    def save(self, file_fp):
        gr_dict = {}
        gr_dict['greenery'] = self.greenery.tolist()
        if self.alpha_map is not None:
            gr_dict['alpha_map'] = self.alpha_map.tolist()
        gr_dict['lat_grid'] = self.lat_grid.tolist()
        gr_dict['long_grid'] = self.long_grid.tolist()
        gr_dict['min_green'] = self.min_green
        gr_dict['max_green'] = self.max_green
        gr_dict['cmap'] = self.cmap
        gr_dict['name'] = self.name

        with open(file_fp, "w") as f:
            json.dump(gr_dict, f, indent=2)


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


def green_map_to_img(green_i, alpha_i, min_green, max_green, cmap="gist_rainbow"):
    delta = (max_green-min_green)
    nx = green_i.shape[0]
    ny = green_i.shape[1]

    green_rgba = np.zeros(green_i.shape+(4,), dtype=np.uint8)
    for irow, row in enumerate(green_i):
        for icol, col in enumerate(row):
            if col < min_green or col > max_green:
                green_rgba[nx-irow-1][icol] = np.zeros(4)
            else:
                step = int(256*(col-min_green)/delta)
                green_rgba[nx-irow-1][icol] = np.array(_cmap2rgb(step, cmap))
                if alpha_i is not None:
                    alpha = alpha_i[irow][icol]
                    green_rgba[nx-irow-1][icol][3] = 255*alpha
#                     print(green_rgba[nx-irow-1][icol])

    return green_rgba


def create_map(green_layers, html_file="index.html"):
    if isinstance(green_layers, MapImageOverlay):
        green_layers = [green_layers]

    for i, gr_layer in enumerate(green_layers):
        green_i = gr_layer.greenery
        alpha_i = gr_layer.alpha_map
        lat_grid = gr_layer.lat_grid
        long_grid = gr_layer.long_grid
        min_green = gr_layer.min_green
        max_green = gr_layer.max_green
        cmap = gr_layer.cmap
        name = gr_layer.name

        if i == 0:
            look_at = [lat_grid.mean(), long_grid.mean()]
            m = folium.Map(location=look_at, zoom_start=15, control_scale=True)

        green_rgba = green_map_to_img(green_i, alpha_i, min_green, max_green, cmap)
        folium.raster_layers.ImageOverlay(
            green_rgba, mercator_project=True, opacity=0.5,
            bounds=_lat_bounds(lat_grid, long_grid),
            name=name
        ).add_to(m)
    folium.LayerControl().add_to(m)
    m.save(html_file)
