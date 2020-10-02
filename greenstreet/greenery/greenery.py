'''
Models to compute a greenery measure from segmentation data.
'''
from abc import abstractmethod, ABC
from math import pi

import numpy as np


class BaseGreenery(ABC):
    name = "base"

    def transform(self, seg_res):
        return self.green_fractions(
            seg_res["seg_map"], seg_res["color_map"][0])

    @abstractmethod
    def green_fractions(self, seg_map, names):
        raise NotImplementedError


class GreeneryWeighted(BaseGreenery):
    "Greenery as the percentage of the pixels from the vegetation class."
    name = "weighted"

    def __init__(self):
        self.partition_sum = {}
        self.weights_store = {}

    def green_fractions(self, seg_map, names):
        shape = seg_map.shape
        if str(shape) not in self.weights_store:
            self.weights_store[str(shape)] = self.weights(shape)

        if str(shape) not in self.partition_sum:
            partition_sum = np.sum(self.weights_store[str(shape)])
            self.partition_sum[str(shape)] = partition_sum

        weights = self.weights_store[str(shape)]
        tot_frac = self.partition_sum[str(shape)]

        counts = np.bincount(seg_map.reshape(-1), weights=weights)
        return dict(zip(names, counts/tot_frac))

    @abstractmethod
    def weights(self, matrix_shape):
        raise NotImplementedError


class CubicWeighted(GreeneryWeighted):
    name = "cubic-weighted"

    def weights(self, matrix_shape):
        idx = np.indices(matrix_shape)
        xval = idx[1].reshape(-1)
        yval = idx[0].reshape(-1)

        dx = 2*xval/matrix_shape[1] - 1
        dy = 2*yval/matrix_shape[0] - 1

        fac = (dx**2+dy**2+1)**-1.5

        return fac


class PanoramaWeighted(GreeneryWeighted):
    "Greenery as the percentage of the pixels from the vegetation class."
    name = "panorama-weighted"

    def weights(self, matrix_shape):
        idx = np.indices(matrix_shape)
        yval = idx[0].reshape(-1)

        dy = (0.5 + yval)/matrix_shape[0]
        fac = np.sin(dy*pi)
        return fac


class GreeneryUnweighted(BaseGreenery):
    name = "unweighted"

    def green_fractions(self, seg_map, names):
        tot_frac = seg_map.shape[0] * seg_map.shape[1]

        counts = np.bincount(seg_map.reshape(-1))
        return dict(zip(names, counts/tot_frac))
