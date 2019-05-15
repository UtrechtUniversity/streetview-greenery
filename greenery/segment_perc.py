'''
Created on 3 May 2019

@author: qubix
'''
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import griddata
from pykrige.ok import OrdinaryKriging
from utils.mapping import green_map_to_img, create_map


class VegetationPercentage(object):
    def __init__(self):
        self._id = "veg_perc"

    def test(self, seg_results):
        if 'vegetation' in seg_results:
            return seg_results['vegetation']
        else:
            return 0.0

    def id(self):
        return self._id


def plot_greenery(green_res, cmap="gist_rainbow"):
    green = np.array(green_res['green'])
    lat = np.array(green_res['lat'])
    long = np.array(green_res['long'])

    lat_grid = np.linspace(lat.min(), lat.max(), num=50)
    long_grid = np.linspace(long.min(), long.max(), num=50)

    xi, yi = np.meshgrid(long_grid, lat_grid)
    green_i = griddata((long, lat), green, (xi, yi), method='linear')

    fig = plt.figure()
    fig.add_subplot(111)

    plt.contourf(xi, yi, green_i, np.linspace(0, 0.75, num=40), cmap=cmap)
    plt.plot(long, lat, 'k.')
    plt.xlabel('xi', fontsize=16)
    plt.ylabel('yi', fontsize=16)
    plt.colorbar()
    plt.show()


def plot_green_krige(green_res, cmap="gist_rainbow", html_file="index.html"):
    n_grid = 200
#     green_list = np.array(green_res['green'])
    lat = np.array(green_res['lat'])
    long = np.array(green_res['long'])

    lat_grid = np.linspace(lat.min(), lat.max(), num=n_grid)
    long_grid = np.linspace(long.min(), long.max(), num=n_grid)
    xi, yi = np.meshgrid(long_grid, lat_grid)

    green = np.zeros((len(green_res["green"]), 3))
    for i in range(len(green_res["green"])):
        green[i][0] = green_res["long"][i]
        green[i][1] = green_res["lat"][i]
        green[i][2] = green_res["green"][i]

    OK = OrdinaryKriging(green[:, 0], green[:, 1], green[:, 2],
                         variogram_model='spherical')
    z, _ = OK.execute('grid', long_grid, lat_grid, backend='loop')

    create_map(z, lat_grid, long_grid, html_file, cmap)
#     plot_grid(xi, yi, z, long, lat, cmap)


def plot_grid(xgrid, ygrid, zgrid, x, y, cmap):
    fig = plt.figure()
    fig.add_subplot(111)

    plt.contourf(xgrid, ygrid, zgrid, np.linspace(0, 0.75, num=40), cmap=cmap)
    plt.plot(x, y, 'k.')
    plt.xlabel('longitude', fontsize=16)
    plt.ylabel('lattitude', fontsize=16)
    plt.colorbar()
    plt.show()
