import numpy as np
from pykrige import OrdinaryKriging

from greenstreet.greenery.semivariogram import _stack_green_res, _lat_long_to_metric


def _compile_greenery(greenery_dict, krige_tiles):
    green_res = {"latitude": [], "longitude": [], "greenery": []}
    for tile_name in krige_tiles:
        for attr in ["latitude", "longitude", "greenery"]:
            green_res[attr].extend(greenery_dict[tile_name][attr])

    return _stack_green_res(green_res)


def krige_greenery(greenery_dict, krige_tiles, tile, init_kwargs={}, dots_per_tile=10):

    coor, green = _compile_greenery(greenery_dict, krige_tiles)
    OK = OrdinaryKriging(coor[:, 0], coor[:, 1], green,
                         **init_kwargs)

    bbox = tile["bbox"]
    lat_grid_degree = np.linspace(bbox[0][0], bbox[1][0])
    long_grid_degree = np.linspace(bbox[0][1], bbox[1][1])
    lat_grid, long_grid = _lat_long_to_metric(lat_grid_degree, long_grid_degree)
    z, _ = OK.execute('grid', long_grid, lat_grid, backend='loop')
    return z

