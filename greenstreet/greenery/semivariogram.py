from math import sqrt, pi, cos

from scipy.spatial.distance import pdist
from matplotlib import pyplot as plt
from tqdm import tqdm
import numpy as np
from pykrige.core import _calculate_variogram_model
from pykrige.variogram_models import spherical_variogram_model
from pykrige.variogram_models import exponential_variogram_model


def _lat_long_to_metric(lat, long):
    lat = np.copy(np.array(lat))
    long = np.copy(np.array(long))

    lat_fac = pi*6356e3/180
    long_fac = lat_fac*cos(pi*52.34/180.0)
    long = long*long_fac
    lat = lat*lat_fac

    return lat, long


def _stack_green_res(green_res):
    if 'greenery' not in green_res:
        return None, None

    lat, long = _lat_long_to_metric(green_res['latitude'],
                                    green_res['longitude'])

    X = np.vstack((long, lat)).T
    z = np.array(green_res['greenery'])
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


def _compute_dist(tile_dist, i_tile_result, j_tile_result):
    i_coor, i_green = _stack_green_res(i_tile_result)
    j_coor, j_green = _stack_green_res(j_tile_result)
    if i_coor is None or j_coor is None:
        return np.array([]), np.array([])

    if tile_dist == 0:
        i_n_sample = i_green.shape[0]
        j_n_sample = i_n_sample
        return _full_dist(i_coor, i_green)
    elif tile_dist > 3:
        return np.array([]), np.array([])
    else:
        i_n_sample = max(i_green.shape[0]/sqrt(10*(tile_dist+1)), 1)
        j_n_sample = max(j_green.shape[0]/sqrt(10*(tile_dist+1)), 1)
        n_sample = round(i_n_sample*j_n_sample)
        max_sample = i_green.shape[0]*j_green.shape[0]
        n_sample = min(max(10000, n_sample), max_sample)
        return _sample_dist(i_coor, i_green, j_coor, j_green, n_sample)


def _semivariance(tile_matrix, result_dict, nlags=None,
                  variogram_model="exponential",
                  plot=False):
    all_dist = []
    all_cor = []

    for ix, iy in np.ndindex(tile_matrix.shape):
        i_name = tile_matrix[ix, iy]["name"]
        i_tile_result = result_dict[i_name]
        for jx, jy in np.ndindex(tile_matrix.shape):
            if tile_matrix[ix, iy]['i_tile'] > tile_matrix[jx, jy]['i_tile']:
                continue
            j_name = tile_matrix[jx, jy]["name"]
            j_tile_result = result_dict[j_name]
            tile_dist = (ix-jx)**2 + (iy-jy)**2
            dist_val, cor_val = _compute_dist(tile_dist, i_tile_result,
                                              j_tile_result)
            all_dist.extend(dist_val)
            all_cor.extend(cor_val)
#             print(ix, iy, jx, jy)
#             print(dist_val, cor_val)

    all_dist = np.array(all_dist)
    all_cor = np.array(all_cor)
#     pbar.close()
    sort_idx = np.argsort(all_dist)
    d = all_dist[sort_idx]
    g = all_cor[sort_idx]
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

