'''
Visualization of greenery measures.
'''

from math import sqrt, pi, cos

import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import griddata

from pykrige import OrdinaryKriging
from pykrige.core import _calculate_variogram_model
from pykrige.variogram_models import spherical_variogram_model,\
    exponential_variogram_model, gaussian_variogram_model

from utils.mapping import MapImageOverlay
from scipy.spatial.distance import euclidean, sqeuclidean, pdist
from matplotlib import pyplot as plt
from tqdm._tqdm import tqdm


def plot_greenery(green_res, cmap="RdYlGn", show=True, title=None):
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
    if title is not None:
        plt.title(title)
    plt.colorbar()
    if show:
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


def krige_greenery(green_res, lat_grid, long_grid, init_kwargs={}, **kwargs):

    coor, green = _stack_green_res(green_res)
    OK = OrdinaryKriging(coor[:, 0], coor[:, 1], green,
                         **init_kwargs)

    lat_grid, long_grid = _lat_long_to_metric(lat_grid, long_grid)
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


def _lat_long_to_metric(lat, long):
    lat = np.copy(np.array(lat))
    long = np.copy(np.array(long))

    lat_fac = pi*6356e3/180
    long_fac = lat_fac*cos(pi*52.34/180.0)
    long = long*long_fac
    lat = lat*lat_fac

    return lat, long


def _stack_green_res(green_res):
    if 'green' not in green_res:
        return None, None

    lat, long = _lat_long_to_metric(green_res['lat'], green_res['long'])

    X = np.vstack((long, lat)).T
    z = np.array(green_res['green'])
    return X, z


def _full_dist(i_coor, i_green):
    all_dist = pdist(i_coor, metric="euclidean")
    all_var = 0.5*pdist(i_green[:, None], metric="sqeuclidean")
    return all_dist, all_var


def euc_dist(a, b):
    return np.sqrt(np.sum((a-b)**2, axis=1))


def _sample_dist(i_coor, i_green, j_coor, j_green, n_sample):

    i_sample_idx = np.random.choice(i_green.shape[0], size=n_sample)
    j_sample_idx = np.random.choice(j_green.shape[0], size=n_sample)
    all_dist = euc_dist(i_coor[i_sample_idx], j_coor[j_sample_idx])
    all_var = 0.5*(i_green[i_sample_idx] - j_green[j_sample_idx])**2

    return all_dist, all_var


def _compute_dist(ix, iy, i_green_res, jx, jy, j_green_res):
    if ix > jx or (ix == jx and iy > jy):
        return np.array([]), np.array([])
    i_coor, i_green = _stack_green_res(i_green_res)
    j_coor, j_green = _stack_green_res(j_green_res)
    if i_coor is None or j_coor is None:
        return np.array([]), np.array([])

    if ix == jx and iy == jy:
        i_n_sample = i_green.shape[0]
        j_n_sample = i_n_sample
        return _full_dist(i_coor, i_green)
    else:
        d_tile = (ix-jx)**2+(iy-jy)**2
        if d_tile > 3:
            return np.array([]), np.array([])
        i_n_sample = max(i_green.shape[0]/sqrt(d_tile+1), 1)
        j_n_sample = max(j_green.shape[0]/sqrt(100*(d_tile+1)), 1)
        n_sample = round(i_n_sample*j_n_sample)
        max_sample = i_green.shape[0]*j_green.shape[0]
        n_sample = min(max(10000, n_sample), max_sample)
        return _sample_dist(i_coor, i_green, j_coor, j_green, n_sample)


def _semivariance(green_matrix, nlags=None, variogram_model="exponential",
                  plot=False):
    all_d = []
    all_g = []
    pbar = tqdm(total=(len(green_matrix)*len(green_matrix[0]))**2)
    for iy, i_green_row in enumerate(green_matrix):
        for ix, i_green_res in enumerate(i_green_row):
            for jy, j_green_row in enumerate(green_matrix):
                for jx, j_green_res in enumerate(j_green_row):
                    pbar.update()
                    dt, gt = _compute_dist(ix, iy, i_green_res, jx, jy, j_green_res)
                    all_d.append(dt)
                    all_g.append(gt)

    all_d = np.concatenate(all_d)
    all_g = np.concatenate(all_g)
    pbar.close()
    sort_idx = np.argsort(all_d)
    d = all_d[sort_idx]
    g = all_g[sort_idx]
    if nlags is None:
        nlags = max(6, min(round(len(d)/10), 200))
    lags = np.zeros(nlags)
    semivariance = np.zeros(nlags)

    for i in range(nlags):
        jm = int(i*d.shape[0]/nlags)
        jp = min(int((i+1)*d.shape[0]/nlags), d.shape[0])
        lags[i] = np.mean(d[jm:jp])
        semivariance[i] = np.mean(g[jm:jp])

    lags = lags[~np.isnan(semivariance)]
    semivariance = semivariance[~np.isnan(semivariance)]

    if variogram_model == "exponential":
        var_fn = exponential_variogram_model
    elif variogram_model == "spherical":
        var_fn = spherical_variogram_model
#     print(nlags, all_d, green_matrix)
#     print(lags)
#     print(semivariance)
    param = _calculate_variogram_model(
        lags, semivariance, variogram_model,
        var_fn, False)

    if plot:
        lags_zero = np.append(0, lags)
        plt.plot(lags, semivariance)
        plt.plot(lags_zero, var_fn(param, lags_zero))
        plt.legend(["data", "variogram model (fit)"])
        plt.xlabel("Distance (m)")
        plt.ylabel("Semivariance")
        plt.ylim([0, 1.1*semivariance.max()])
        plt.xlim([0, lags.max()])
        print(param)
        plt.show()

    param[2] = max(1e-5, param[2])
    param[0] += param[2]

    krige_kwargs = {
        "variogram_model": variogram_model,
        "variogram_parameters": param.tolist(),
    }
    return krige_kwargs


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
