#!/usr/bin/env python

import os

import numpy as np
import matplotlib

from API import AdamPanoramaManager
from utils.selection import select_bbox, select_seg_model, select_green_model
import matplotlib.pyplot as plt
from models.deeplab import plot_segmentation
from greenery.visualization import plot_greenery
from utils.mapping import create_map
from API.tile_manager import TileManager
from sklearn.linear_model.base import LinearRegression


def _del_green(green_res, i):
    for key in green_res:
        del green_res[key][i]


def _remove_missing(green_res_x, green_res_y):
    i = 0
    while i < len(green_res_x["green"]):
        if green_res_x["lat"][i] == green_res_y["lat"][i]:
            i += 1
            continue
        try:
            if green_res_x["lat"][i] == green_res_y["lat"][i+1]:
                _del_green(green_res_y, i)
        except IndexError:
            pass
        try:
            if green_res_x["lat"][i+1] == green_res_y["lat"][i]:
                _del_green(green_res_x, i)
        except IndexError:
            pass
        i += 1


def compare_green_measures(X_measure, y_measure, **kwargs):
    X_green_kwargs = select_green_model(X_measure)
    y_green_kwargs = select_green_model(y_measure)

    X_tiler = TileManager(**X_green_kwargs, **kwargs)
    y_tiler = TileManager(**y_green_kwargs, **kwargs)

    X_green = X_tiler.green_direct()
    y_green = y_tiler.green_direct()

    X_gval = np.array(X_green["green"])
    y_gval = np.array(y_green["green"])
    y_gval = y_gval/(1-X_gval)
    X_gval = X_gval.reshape(-1, 1)

    reg = LinearRegression().fit(X_gval, y_gval)
    plt.figure()
    plt.scatter(X_gval.reshape(-1), y_gval)
    x = np.arange(0, X_gval.max()+0.1, 0.01)
    myplot, = plt.plot(x, reg.predict(x.reshape(-1, 1)))
    if reg.coef_[0] < 0:
        sgn = "- "
    else:
        sgn = "+ "
    lgd = f"{round(reg.intercept_,2)} {sgn}{abs(round(reg.coef_[0], 2))} x"
    plt.legend([myplot], [lgd], loc="upper right")
    plt.xlabel(X_measure)
    plt.ylabel(y_measure)
    plt.title(f"score: {round(reg.score(X_gval, y_gval),3)}")
    plt.show()


def compare_panorama_cubic(greenery_measure="vegetation", **kwargs):
    green_kwargs = select_green_model(greenery_measure)

    panorama_tiler = TileManager(cubic_pictures=False, **kwargs, **green_kwargs)
    cubic_tiler = TileManager(cubic_pictures=True, **kwargs, **green_kwargs)

    panorama_green = panorama_tiler.green_direct()
    cubic_green = cubic_tiler.green_direct()

    _remove_missing(panorama_green, cubic_green)
    x = np.arange(0, 0.8, 0.01)

    x_pano = np.array(panorama_green["green"]).reshape(-1, 1)
    y_cubic = np.array(cubic_green["green"])
    reg = LinearRegression().fit(x_pano, y_cubic)
    print(reg.score(x_pano, y_cubic))
    print(reg.coef_[0], reg.intercept_)
    plt.figure()
    plt.scatter(panorama_green["green"], cubic_green["green"])
    plt.plot(x, reg.predict(x.reshape(-1, 1)))
    plt.xlabel("panoramas")
    plt.ylabel("cubic")
    plt.xlim(0, max(0.001, max(panorama_green["green"])*1.1))
    plt.ylim(0, max(0.001, max(cubic_green["green"])*1.1))

    plot_greenery(panorama_green, show=False, title="panorama")
    plot_greenery(cubic_green, show=False, title="cubic")
    plt.show()


def main():
    area = "oosterpark"
    model = "deeplab-mobilenet"
    grid_level = 3

    x_green = "vegetation"
    y_green = "building"

    compare_cubic = False

    if len(os.sys.argv) > 1:
        par = os.sys.argv[1].split("-")
        assert(len(par) == 2)
        if par[0] == "cubic":
            compare_cubic = True
            x_green = par[1]
        else:
            x_green = par[0]
            y_green = par[1]

    bbox = select_bbox(area)
    seg_kwargs = select_seg_model(model)

    if compare_cubic:
        compare_panorama_cubic(x_green, bbox=bbox, **seg_kwargs,
                               grid_level=grid_level)
    else:
        compare_green_measures(x_green, y_green, bbox=bbox,
                               **seg_kwargs,
                               cubic_pictures=True, grid_level=grid_level)


if __name__ == "__main__":
    main()
