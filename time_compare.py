#!/usr/bin/env python

import os
import datetime

import numpy as np
from sklearn.linear_model.base import LinearRegression
import matplotlib.pyplot as plt

from utils.selection import select_bbox, select_seg_model, select_green_model
from greenery.visualization import plot_greenery
from API.tile_manager import TileManager


def _del_green(green_res, i):
    "Delete a single item from green results."
    for key in green_res:
        del green_res[key][i]


def _remove_missing(green_res_x, green_res_y):
    """ To be able to compare among different sources (panorama vs cubic),
        We have to align the data. Here, the assumption is that they are
        already nearly aligned, with a few pictures missing here and there.
        The ones available in one, that are missing in the other are deleted.
    """
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


def compare_time(green, time_measure="year", **kwargs):
    """ Compare/plot two different green measures with the same segmentation
        engine/settings. Apply simple linear regression to figure out if there
        is correlation between the different variables.
    """

    green_kwargs = select_green_model(green)

    tiler = TileManager(cubic_pictures=False, **green_kwargs, **kwargs)

    green_res = tiler.green_direct()

    sorted_res = {}
    for i in range(len(green_res["green"])):
        dt_str = green_res["timestamp"][i]
        green = green_res["green"][i]
        dt = datetime.datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%fZ")

        if time_measure == "year":
            tm = dt.year
        elif time_measure == "month":
            tm = dt.month
        elif time_measure == "hour":
            tm = dt.hour
        if tm in sorted_res:
            sorted_res[tm][0] += green
            sorted_res[tm][1] += 1
        else:
            sorted_res[tm] = [green, 1]
    tm_array = np.zeros(len(sorted_res))
    green_val = np.zeros(len(sorted_res))

    i = 0
    for tm in sorted_res:
        tm_array[i] = tm
        green_val[i] = sorted_res[tm][0]/sorted_res[tm][1]
        i += 1

    print(tm_array, green_val)

    plt.figure()
    plt.scatter(tm_array, green_val)
    plt.show()


def compare_panorama_cubic(greenery_measure="vegetation", **kwargs):
    """ Compare/plot the segmentation results of panoramic and cubic
        images to each other. Also use linear regression to determine
        how they relate to each other.
    """

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
    """ There is one CLI argument currently available:
        the type of analysis to perform. This takes the form cubic-{class}, or
        {class1}-{class2}, with {class} being one of the cityscape classes,
        such as "vegetation", "road", "building", etc.
        Adjust area, grid_level, segmentation model directly in the script.
    """

    area = "oosterpark"
    model = "deeplab-mobilenet"
    grid_level = 4

    green = "vegetation"
    time_measure = "month"

    bbox = select_bbox(area)
    seg_kwargs = select_seg_model(model)

    compare_time(green, time_measure=time_measure, bbox=bbox, **seg_kwargs,
                 grid_level=grid_level)

if __name__ == "__main__":
    main()
