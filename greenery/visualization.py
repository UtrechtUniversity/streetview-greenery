'''
Visualization of greenery measures.
'''

import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import griddata
from pykrige.ok import OrdinaryKriging
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


def create_kriged_overlay(green_res=None, grid=[200, 200], cmap="gist_rainbow",
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
    # Load overlay from file if available.
    try:
        overlay = MapImageOverlay(overlay_fp)
        return overlay
    except FileNotFoundError:
        pass

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

    overlay = MapImageOverlay(z, lat_grid, long_grid, cmap=cmap, name=name)
    overlay.save(overlay_fp)
    return overlay


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
