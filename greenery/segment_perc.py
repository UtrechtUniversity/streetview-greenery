'''
Created on 3 May 2019

@author: qubix
'''
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import griddata


class VegetationPercentage(object):
    def __init__(self):
        self._id = "veg_perc"

    def test(self, seg_results):
        seg_map = np.array(seg_results['seg_map'])
        names = np.array(seg_results['color_map'][0])

        veg_id = np.where(names == "vegetation")[0]
        veg_counts = np.count_nonzero(seg_map == veg_id, axis=None)
        greenery = veg_counts/seg_map.size
#         print(greenery)
#     _, veg_counts = np.unique(seg_map.reshape(-1), return_counts=True)
        return greenery

    def id(self):
        return self._id


def plot_greenery(green_res):
    green = np.array(green_res['green'])
    lat = np.array(green_res['lat'])
    long = np.array(green_res['long'])

    lat_grid = np.linspace(lat.min(), lat.max(), num=50)
    long_grid = np.linspace(long.min(), long.max(), num=50)

    xi, yi = np.meshgrid(long_grid, lat_grid)
    green_i = griddata((long, lat), green, (xi, yi), method='linear')
#     print(xi.shape, yi.shape, green_i.shape)
    fig = plt.figure()
    ax = fig.add_subplot(111)
    plt.contourf(xi, yi, green_i, np.linspace(0, 0.75, num=40), cmap="gist_rainbow")
    plt.plot(long, lat, 'k.')
    plt.xlabel('xi', fontsize=16)
    plt.ylabel('yi', fontsize=16)
    plt.colorbar()
    plt.show()

