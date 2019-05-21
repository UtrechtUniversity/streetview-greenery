'''

'''
import os
from math import cos, pi

import numpy as np

from API.adam_manager import AdamPanoramaManager


class AdamPanoramaTile(AdamPanoramaManager):
    def __init__(self, tile_name="unknown",
                 **kwargs):
        super(AdamPanoramaTile, self).__init__(**kwargs)
        self.tile_name = tile_name
        self.data_dir = os.path.join(self.data_dir, self.tile_name)

    def get(self, bbox=[[52.45, 4.93], [52.35, 4.935]],
            **kwargs):
        if bbox[0][0] < bbox[1][0]:
            t = bbox[0][0]
            bbox[0][0] = bbox[1][0]
            bbox[1][0] = t

        if bbox[0][1] > bbox[1][1]:
            t = bbox[0][1]
            bbox[0][1] = bbox[1][1]
            bbox[1][1] = t

        bb_string = str(bbox[0][1]) + "," + str(bbox[0][0]) + "," + \
            str(bbox[1][1]) + "," + str(bbox[1][0])
        self.bbox = bbox
        self.bb_string = bb_string

        super(AdamPanoramaTile, self).get(bbox=self.bb_string, **kwargs)

    def load(self, n_sample=None, grid_level=None):
        if grid_level is None:
            super(AdamPanoramaTile, self).load(n_sample=n_sample)
            return

        nx = 2**grid_level
        ny = 2**grid_level
        x_start = self.bbox[0][1]
        x_end = self.bbox[1][1]
        y_start = self.bbox[1][0]
        y_end = self.bbox[0][0]

#         R_earth = 6356e3  # meters
#         dy_target = 180*resolution/(R_earth*pi)
#         dx_target = dy_target/cos(y_start)

#         nx = ceil((x_end-x_start)/dx_target)
#         ny = ceil((y_end-y_start)/dy_target)
        dx = (x_end-x_start)/nx
        dy = (y_end-y_start)/ny

#         print(nx)
#         print(ny)
        print(f"Target resolution: {pi*dy/180*6356e3} m")

        sample_list = [[] for i in range(nx)]
        for i in range(nx):
            sample_list[i] = [[] for i in range(ny)]

        for i, meta in enumerate(self.meta_data):
            x = meta["geometry"]["coordinates"][0]
            y = meta["geometry"]["coordinates"][1]
            ix = int((x-x_start)/dx)
            iy = int((y-y_start)/dy)
#             print(ix, iy, x, y)
#             print(x, y)
            try:
                sample_list[ix][iy].append(i)
            except IndexError:
                pass

#         print(sample_list)
        load_ids = []
        for ix in range(nx):
            for iy in range(ny):
                cur_list = sample_list[ix][iy]
                if not len(cur_list):
                    continue
                min_dist = 10.0**10
                idx_min = -1
                x_base = x_start + dx*ix
                y_base = y_start + dy*iy
#                 print(y_base, x_base)
                x_fac = 1/cos(x_base)
                for i_meta in cur_list:
                    meta = self.meta_data[i_meta]
                    x = meta["geometry"]["coordinates"][0]
                    y = meta["geometry"]["coordinates"][1]
                    dist = ((x-x_base)*x_fac)**2 + (y-y_base)**2
#                     print(dist)
                    if dist < min_dist:
                        idx_min = i_meta
                        min_dist = dist

                load_ids.append(idx_min)
        load_ids = np.array(load_ids)
        super(AdamPanoramaTile, self).load(load_ids=load_ids)