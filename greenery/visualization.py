'''
Visualization of greenery measures.
'''

import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import griddata

from pykrige import OrdinaryKriging

from utils.mapping import MapImageOverlay


def plot_greenery(green_res, cmap="gist_rainbow"):
    """
    Plot a map of the greenery values with matplotlib.

    Arguments
    ---------
    green_res: dict
        Dictionary with three keys: 'green', 'lat', 'long', containing
        the coordinates and greenery values.
    cmap: str
        Colormap as defined by matplotlib.
    """
    green = np.array(green_res['green'])
    lat = np.array(green_res['lat'])
    long = np.array(green_res['long'])

    # Create a linear grid with 50 data points and linear interpolation.
    lat_grid = np.linspace(lat.min(), lat.max(), num=50)
    long_grid = np.linspace(long.min(), long.max(), num=50)

    xi, yi = np.meshgrid(long_grid, lat_grid)
    green_i = griddata((long, lat), green, (xi, yi), method='linear')

    # Plot contourmap
    fig = plt.figure()
    fig.add_subplot(111)
    plt.contourf(xi, yi, green_i, np.linspace(0, 0.75, num=40), cmap=cmap)
    plt.plot(long, lat, 'k.')
    plt.xlabel('longitude', fontsize=16)
    plt.ylabel('latitude', fontsize=16)
    plt.colorbar()
    plt.show()


def create_kriged_overlay(green_res, grid=[200, 200], cmap="gist_rainbow",
                          overlay_fp="krige_map.json", name=None,
                          n_closest_points=None):
    """
    Create an overlay for openstreetmap using kriging as interpolation.

    Arguments
    ---------
    green_res: dict
        Contains greenery values with coordinates.
    n_grid: int
        Number of grid points.
    cmap: str
        Matplotlib color map.
    overlay_fp: str
        Filepath to store kriged map. Use as cache if available.
    name: str
        Name to give to the overlay.
    n_closest_points: int
        Used in kriging procedure to limit memory/compute time.
    """
#     Load overlay from file if available.
#     try:
#         overlay = MapImageOverlay(overlay_fp)
#         return overlay
#     except FileNotFoundError:
#         pass

    if name is None:
        name = overlay_fp

    lat = np.array(green_res['lat'])
    long = np.array(green_res['long'])

    lat_grid = np.linspace(lat.min(), lat.max(), num=grid[1])
    long_grid = np.linspace(long.min(), long.max(), num=grid[0])

    green = np.zeros((len(green_res["green"]), 3))
    for i in range(len(green_res["green"])):
        green[i][0] = green_res["long"][i]
        green[i][1] = green_res["lat"][i]
        green[i][2] = green_res["green"][i]

    OK = OrdinaryKriging(green[:, 0], green[:, 1], green[:, 2],
                         variogram_model='spherical')
    z, _ = OK.execute('grid', long_grid, lat_grid, backend='loop',
                      n_closest_points=n_closest_points)

    alpha_map = _alpha_from_coordinates(lat, long, grid)
    overlay = MapImageOverlay(z, lat_grid=lat_grid, long_grid=long_grid,
                              alpha_map=alpha_map,
                              cmap=cmap, name=name)
    overlay.save(overlay_fp)
    return overlay


def krige_greenery(green_res, lat_grid, long_grid, **kwargs):
    green = np.zeros((len(green_res["green"]), 3))
    for i in range(len(green_res["green"])):
        green[i][0] = green_res["long"][i]
        green[i][1] = green_res["lat"][i]
        green[i][2] = green_res["green"][i]

    OK = OrdinaryKriging(green[:, 0], green[:, 1], green[:, 2],
                         variogram_model='spherical')
    z, _ = OK.execute('grid', long_grid, lat_grid, backend='loop',
                      **kwargs)
    return z


def _plot_grid(xgrid, ygrid, zgrid, x, y, cmap):
    " Help function to plot grid data (not used at the moment). "
    fig = plt.figure()
    fig.add_subplot(111)

    plt.contourf(xgrid, ygrid, zgrid, np.linspace(0, 0.75, num=40), cmap=cmap)
    plt.plot(x, y, 'k.')
    plt.xlabel('longitude', fontsize=16)
    plt.ylabel('lattitude', fontsize=16)
    plt.colorbar()
    plt.show()


def _alpha(dist, min_dist, max_dist):
    if dist <= min_dist:
        return 1
    return (max_dist-dist)/(max_dist-min_dist)


# def _alpha_from_coordinates(lat, long, grid, min_dist=1, max_dist=6):
#     lat_min = lat.min()
#     lat_max = lat.max() + 10*len(lat)*np.finfo(float).eps
#     long_min = long.min()
#     long_max = long.max() + 10*len(lat)*np.finfo(float).eps
#     n_lat = grid[1]
#     n_long = grid[0]
#     d_lat = (lat_max-lat_min)/n_lat
#     d_long = (long_max-long_min)/n_long
# 
#     dist_graph = np.zeros((n_lat, n_long))
# 
#     for i_sample in range(len(lat)):
#         i_lat = int((lat[i_sample]-lat_min)/d_lat)
#         i_long = int((long[i_sample]-long_min)/d_long)
#         dist_graph[i_lat][i_long] = 1
#     for i_dist in range(max_dist):
#         alpha = _alpha(i_dist, min_dist, max_dist)
#         new_graph = np.zeros(dist_graph.shape)
#         for i_lat in range(n_lat):
#             for i_long in range(n_long):
#                 if dist_graph[i_lat][i_long]:
#                     continue
#                 # South
#                 if i_lat and dist_graph[i_lat-1][i_long]:
#                     new_graph[i_lat][i_long] = alpha
#                 # West
#                 elif i_long and dist_graph[i_lat][i_long-1]:
#                     new_graph[i_lat][i_long] = alpha
#                 # North
#                 elif i_lat+1 < n_lat and dist_graph[i_lat+1][i_long]:
#                     new_graph[i_lat][i_long] = alpha
#                 # East
#                 elif i_long+1 < n_long and dist_graph[i_lat][i_long+1]:
#                     new_graph[i_lat][i_long] = alpha
#         dist_graph = dist_graph + new_graph
#     return dist_graph


def _alpha_from_coordinates(green_res, lat_grid, long_grid, min_dist=1, max_dist=6):
    lat = green_res['lat']
    long = green_res['long']
    lat_min = lat_grid.min()
    long_min = long_grid.min()
    n_lat = lat_grid.size
    n_long = long_grid.size
    d_lat = lat_grid[1]-lat_grid[0]
    d_long = long_grid[1]-long_grid[0]

    dist_graph = np.zeros((n_lat, n_long))

    for i_sample in range(len(lat)):
        i_lat = int((lat[i_sample]-lat_min)/d_lat)
        i_long = int((long[i_sample]-long_min)/d_long)
        dist_graph[i_lat][i_long] = 1
    for i_dist in range(max_dist):
        alpha = _alpha(i_dist, min_dist, max_dist)
        new_graph = np.zeros(dist_graph.shape)
        for i_lat in range(n_lat):
            for i_long in range(n_long):
                if dist_graph[i_lat][i_long]:
                    continue
                # South
                if i_lat and dist_graph[i_lat-1][i_long]:
                    new_graph[i_lat][i_long] = alpha
                # West
                elif i_long and dist_graph[i_lat][i_long-1]:
                    new_graph[i_lat][i_long] = alpha
                # North
                elif i_lat+1 < n_lat and dist_graph[i_lat+1][i_long]:
                    new_graph[i_lat][i_long] = alpha
                # East
                elif i_long+1 < n_long and dist_graph[i_lat][i_long+1]:
                    new_graph[i_lat][i_long] = alpha
        dist_graph = dist_graph + new_graph
    return dist_graph


