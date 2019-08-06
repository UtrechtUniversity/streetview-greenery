#!/usr/bin/env python

import os
import datetime
import sys

import numpy as np
from sklearn.linear_model.base import LinearRegression
import matplotlib.pyplot as plt
from pysolar.solar import get_altitude_fast
from tqdm import tqdm
from math import sqrt
from pandas.plotting import register_matplotlib_converters

from utils.selection import select_bbox, select_seg_model, select_green_model
from greenery.visualization import plot_greenery
from API.tile_manager import TileManager
from scipy.stats import stats
from utils.sun import Sun, fast_coor_to_dist
from utils.time_conversion import get_time_from_str
from utils.sun import degree_to_meter

def _del_green(green_res, i):
    "Delete a single item from green results."
    for key in green_res:
        del green_res[key][i]


def _rearrange_green_res(green_res, max_range=10):
    avg_lat = np.mean(np.array(green_res["lat"]))
    lat_fac, long_fac = degree_to_meter(avg_lat)
    new_green = []
    cur_green = [0]
    cur_lat = green_res["lat"][0]
    cur_long = green_res["long"][1]
    for i in range(1, len(green_res["green"])):
        lat = green_res["lat"][i]
        long = green_res["long"][i]
        dist = sqrt(((lat-cur_lat)*lat_fac)**2 + ((long-cur_long)*long_fac)**2)
        if dist > max_range:
            new_green.append(cur_green)
            cur_green = []
            cur_lat = green_res["lat"][i]
            cur_long = green_res["long"][i]
        cur_green.append(i)
    new_green.append(cur_green)
    return new_green


def compare_time(green, time_measure="year", **kwargs):
    """ Compare/plot two different green measures with the same segmentation
        engine/settings. Apply simple linear regression to figure out if there
        is correlation between the different variables.
    """

    green_kwargs = select_green_model(green)

    tiler = TileManager(cubic_pictures=True, **green_kwargs, **kwargs)

    green_res = tiler.green_direct()

    spotted_green = _rearrange_green_res(green_res)
#     print(spotted_green)
    sorted_res = {}
    long_res = {}
    sun = Sun()
    x_label=time_measure
    y_label="greenery"
    x_res = {}
    tm_avail = {}
    overall_avg = 0
    register_matplotlib_converters()
    for comp_list in tqdm(spotted_green):
        overall_avg += np.mean(np.array(green_res["green"])[comp_list])/len(spotted_green)
        if len(comp_list) < 2:
            continue
        tm_val = []
        green_val = []
        for i in range(len(comp_list)):
            idx = comp_list[i]                
            dt_str = green_res["timestamp"][idx]
            green = green_res["green"][idx]
            lat = green_res["lat"][idx]
            long = green_res["long"][idx]
            dt = get_time_from_str(dt_str)
            dt = dt.replace(tzinfo=datetime.timezone.utc)
            if time_measure == "year":
                tm = dt.year
            elif time_measure == "month":
                tm = dt.month
            elif time_measure == "day":
                tm = dt.day
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
            tm_val.append(tm)
            green_val.append(green)
            if tm not in tm_avail:
                tm_avail[tm] = 0
        for i in range(len(comp_list)):
            for j in range(i+1, len(comp_list)):
                green_i = green_val[i]
                green_j = green_val[j]
                tm_i = tm_val[i]
                tm_j = tm_val[j]
                if tm_i not in x_res:
                    x_res[tm_i] = {}
                if tm_j not in x_res[tm_i]:
                    x_res[tm_i][tm_j] = np.zeros(2)
#                 if abs(green_i-green_j) > 0.1:
#                     idx_i = comp_list[i]
#                     idx_j = comp_list[j]
#                     lat_i = green_res["lat"][idx_i]
#                     lat_j = green_res["lat"][idx_j]
#                     long_i = green_res["long"][idx_i]
#                     long_j = green_res["long"][idx_j]
#                     dist = fast_coor_to_dist(lat_i, long_i, lat_j, long_j)
#                     print(lat_i, long_i, lat_j, long_j)
#                     print(idx_i, idx_j, dist, comp_list)
#                     print(green_res["pano_id"][idx_i], green_res["pano_id"][idx_j])
#                     exit()
                x_res[tm_i][tm_j] += np.array([1, green_i-green_j])
    
    single_res = {}
    for tm_i in x_res:
        for tm_j in x_res[tm_i]:
            if tm_i not in single_res:
                single_res[tm_i] = 0
            if tm_j not in single_res:
                single_res[tm_j] = 0
            new_avg = x_res[tm_i][tm_j][1]/x_res[tm_i][tm_j][0]/(2*(len(tm_avail)-1))
            single_res[tm_i] += new_avg
            single_res[tm_j] -= new_avg
    tm_array = np.array(list(single_res.keys()))
    green_avg = np.array(list(single_res.values())) + overall_avg
#             print(f"{tm_i} += {new_avg}, {tm_j} -= {new_avg}")
#     print(x_res)
#     print(single_res)
#     exit()

#         if tm in sorted_res:
#             sorted_res[tm][0] += green
#             sorted_res[tm][1] += 1
#         else:
#             sorted_res[tm] = [green, 1]
#     tm_array = np.zeros(len(sorted_res))
#     green_avg = np.zeros(len(sorted_res))
#     green_err = np.zeros(len(sorted_res))
# 
#     long_avg = np.zeros(len(sorted_res))
#     long_err = np.zeros(len(sorted_res))
# 
#     i = 0
#     for tm in sorted_res:
#         tm_array[i] = tm
#         green_avg[i] = np.array(sorted_res[tm]).mean()
#         green_err[i] = stats.sem(np.array(sorted_res[tm]))
#         long_avg[i] = np.array(long_res[tm]).mean()
#         long_err[i] = stats.sem(np.array(long_res[tm]))
#         i += 1


    order = np.argsort(tm_array)
    if time_measure == "all_month":
        new_array = []
        for tm in tm_array:
            new_array.append(datetime.date(2016+tm//12, (tm%12)+1, 15))
        tm_array = np.array(new_array)
        
#     print(tm_array, green_avg)
#     print(green_res["timestamp"])
    plt.figure()
    plt.scatter(tm_array[order], green_avg[order])
    plt.xlabel(x_label)
    plt.ylabel(y_label)
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
    grid_level = 2

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
