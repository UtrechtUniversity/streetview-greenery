#!/usr/bin/env python

import os
import datetime
import sys

import numpy as np
from sklearn.linear_model.base import LinearRegression
import matplotlib.pyplot as plt
from pysolar.solar import get_altitude_fast
from tqdm import tqdm

from utils.selection import select_bbox, select_seg_model, select_green_model
from greenery.visualization import plot_greenery
from API.tile_manager import TileManager
from scipy.stats import stats
from utils.sun import Sun
from utils.time_conversion import get_time_from_str


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

    tiler = TileManager(cubic_pictures=True, **green_kwargs, **kwargs)

    green_res = tiler.green_direct()

    sorted_res = {}
    long_res = {}
    sun = Sun()
    x_label="?"
    y_label="greenery"
    for i in tqdm(range(len(green_res["green"]))):
        dt_str = green_res["timestamp"][i]
        green = green_res["green"][i]
        lat = green_res["lat"][i]
        long = green_res["long"][i]
        dt = get_time_from_str(dt_str)
        dt = dt.replace(tzinfo=datetime.timezone.utc)
        if time_measure == "year":
            tm = dt.year
        elif time_measure == "month":
            tm = dt.month
        elif time_measure == "all_month":
            tm = (dt.year-2016)*12 + dt.month-1
        elif time_measure == "hour":
            tm = sun.timeToDawnDusk(dt, longitude=long, latitude=lat, time_zone='UTC')
            tm = round(tm*4, 0)/4
        elif time_measure == "sun_angle":
            tm = round(get_altitude_fast(lat, long, dt)/2, 0)*2
            x_label="Sun altitude (degrees)"
        elif time_measure == "minute":
            tm = dt.minute
        elif time_measure == "second":
            tm = dt.second
        try:
            sorted_res[tm].append(green)
            long_res[tm].append(long)
        except KeyError:
            sorted_res[tm] = []
            sorted_res[tm].append(green)
            long_res[tm] = []
            long_res[tm].append(long)
#         if tm in sorted_res:
#             sorted_res[tm][0] += green
#             sorted_res[tm][1] += 1
#         else:
#             sorted_res[tm] = [green, 1]
    tm_array = np.zeros(len(sorted_res))
    green_avg = np.zeros(len(sorted_res))
    green_err = np.zeros(len(sorted_res))

    long_avg = np.zeros(len(sorted_res))
    long_err = np.zeros(len(sorted_res))

    i = 0
    for tm in sorted_res:
        tm_array[i] = tm
        green_avg[i] = np.array(sorted_res[tm]).mean()
        green_err[i] = stats.sem(np.array(sorted_res[tm]))
        long_avg[i] = np.array(long_res[tm]).mean()
        long_err[i] = stats.sem(np.array(long_res[tm]))
        i += 1


    order = np.argsort(tm_array)
#     print(tm_array, green_avg, green_err)

    plt.figure()
    plt.errorbar(tm_array[order], green_avg[order], green_err[order])
    plt.xlabel(x_label)
    plt.ylabel(y_label)
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
    grid_level = 3

    green = "vegetation"
    time_measure = "month"
    
    if len(sys.argv) > 1:
        time_measure = sys.argv[1]
    if len(sys.argv) > 2:
        green = sys.argv[2]

    bbox = select_bbox(area)
    seg_kwargs = select_seg_model(model)

    compare_time(green, time_measure=time_measure, bbox=bbox, **seg_kwargs,
                 grid_level=grid_level)

if __name__ == "__main__":
    main()
