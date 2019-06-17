'''
Models to compute a greenery measure from segmentation data.
'''
import numpy as np


def compute_total_frac(matrix_shape):
    idx = np.indices(matrix_shape)
    xval = idx[1].reshape(-1)
    yval = idx[0].reshape(-1)

    dx = 2*xval/matrix_shape[1] - 1
    dy = 2*yval/matrix_shape[0] - 1

    fac = (dx**2+dy**2+1)**-1.5

    return np.sum(fac)


def compute_weights(matrix_shape):
    idx = np.indices(matrix_shape)
    xval = idx[1].reshape(-1)
    yval = idx[0].reshape(-1)

    dx = 2*xval/matrix_shape[1] - 1
    dy = 2*yval/matrix_shape[0] - 1

    fac = (dx**2+dy**2+1)**-1.5

    return fac


class ClassPercentage(object):
    " Greenery as the percentage of the pixels from the vegetation class. "
    def __init__(self, myclass="vegetation"):
        self.myclass = myclass
        self._id = f"class_percentage"
        self.tot_frac = {}
        self.weights = {}

    def test(self, seg_results):
        try:
            return seg_results[self.myclass]
        except KeyError:
            return 0.0

    def test_seg_map(self, seg_map, names):
        try:
            class_id = np.where(names == self.myclass)[0][0]
        except IndexError:
            raise ValueError(f"Error: class {self.myclass} doesn't exist.")

        idx = np.where(seg_map == class_id)
        xval = idx[1]
        yval = idx[0]

        dx = 2*xval/seg_map.shape[1] - 1
        dy = 2*yval/seg_map.shape[0] - 1

        fac = (dx**2+dy**2+1)**-1.5

        if str(seg_map.shape) not in self.tot_frac:
            self.tot_frac[str(seg_map.shape)] = compute_total_frac(seg_map.shape)

#         print(self.tot_frac[str(seg_map.shape)])
        return np.sum(fac)/self.tot_frac[str(seg_map.shape)]

    def test_seg_map2(self, seg_map, names):
        shape = seg_map.shape
        if str(shape) not in self.weights:
            self.weights[str(shape)] = compute_weights(shape)

        if self.tot_frac is None or str(shape) not in self.tot_frac:
            self.tot_frac[str(shape)] = compute_total_frac(shape)

        weights = self.weights[str(shape)]
        tot_frac = self.tot_frac[str(shape)]

        counts = np.bincount(seg_map.reshape(-1), weights=weights)
#         print(np.sum(counts/tot_frac))
        return dict(zip(names, counts/tot_frac))

    def id(self, one_class=False):
        " Identification of the measure. "
        if one_class:
            return self.myclass
        else:
            return self._id
