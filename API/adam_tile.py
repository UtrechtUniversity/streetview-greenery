'''
This is the tile manager for the data.amsterdam API.
It derives from the AdamPanoramaManager, but specifically works with
tiles instead of circles.
'''

import os
from math import cos, pi, sqrt
import json

import numpy as np

from API.adam_manager import AdamPanoramaManager
from utils import _empty_green_res
from API.idgen import get_green_key
from utils.time_conversion import get_time_from_str
from utils.sun import degree_to_meter, fast_coor_to_dist

def get_close_neighbors(mini_tile_list, mini_x, mini_y, x_base, y_base, year_base, x_fac,
                        y_fac, meta_data, max_dist=10):
    neighbors = {}
    for ix in range(mini_x-1, mini_x+2):
        if ix < 0 or ix >= len(mini_tile_list):
            continue
        for iy in range(mini_y-1, mini_y+2):
            if iy < 0 or iy >= len(mini_tile_list[ix]):
                continue
            for i_meta in mini_tile_list[ix][iy]:
                meta = meta_data[i_meta]
                x = meta["geometry"]["coordinates"][0]
                y = meta["geometry"]["coordinates"][1]
                dt = get_time_from_str(meta["timestamp"])
                if dt.year == year_base:
                    continue

                dist = sqrt(((x-x_base)*x_fac)**2 + ((y-y_base)*y_fac)**2)
                if dist > max_dist:
                    continue
                if dt.year in neighbors and neighbors[dt.year]["dist"] < dist:
                    continue
                elif dt.year not in neighbors:
                    neighbors[dt.year] = {}
                neighbors[dt.year]["dist"] = dist
                neighbors[dt.year]["imeta"] = i_meta
    nlist = []
    for year in neighbors:
        nlist.append(neighbors[year]["imeta"])
    return nlist


class AdamPanoramaTile(AdamPanoramaManager):
    def __init__(self, tile_name="unknown",
                 bbox=[[52.35, 4.93], [52.45, 4.935]],
                 grid_level=None,
                 all_years=False,
                 **kwargs):
        super(AdamPanoramaTile, self).__init__(**kwargs)
        self.tile_name = tile_name
        self.data_dir = os.path.join(self.data_dir, "tiles", self.tile_name)

        # Use southwest - northeast bounding box definition.
        if bbox[0][0] > bbox[1][0]:
            t = bbox[0][0]
            bbox[0][0] = bbox[1][0]
            bbox[1][0] = t

        if bbox[0][1] > bbox[1][1]:
            t = bbox[0][1]
            bbox[0][1] = bbox[1][1]
            bbox[1][1] = t

        # Get the bounding box for data.amsterdam API.
        bb_string = str(bbox[0][1]) + "," + str(bbox[1][0]) + "," + \
            str(bbox[1][1]) + "," + str(bbox[0][0])
        self.bbox = bbox
        self.bb_string = bb_string
        self.grid_level = grid_level
        self.all_years = all_years

    def get(self, **kwargs):
        super(AdamPanoramaTile, self).get(bbox=self.bb_string, **kwargs)

    def load(self, verbose=True, max_range=7, **kwargs):
        """
        Compute which panorama's should be (down)loaded, load those.

        Arguments
        ---------
        grid_level: int
            Level of detail of the grid. Level 0 is one grid point per tile.
            Level 1 would be 4 grid points (2 in each dimension).
        verbose: bool
            Print messages to terminal or not.
        """
        # If no grid level behave as super class (AdamPanoramaManager).
        grid_level = self.grid_level
        all_years = self.all_years
        if grid_level is None:
            super(AdamPanoramaTile, self).load(**kwargs)
            return

        # Grid level is similar to a zoom level.
        # nx: number of points in x-direction.
        nx = 2**grid_level
        ny = 2**grid_level

        # x <-> longitude, y <-> latitude
        x_start = self.bbox[0][1]
        x_end = self.bbox[1][1]
        y_start = self.bbox[0][0]
        y_end = self.bbox[1][0]

        # Difference in degrees between measure points.
        dx = (x_end-x_start)/nx
        dy = (y_end-y_start)/ny

        # Print the resolution of the grid points.
        if verbose:
            R_earth = 6356e3  # meters]
            yres = pi*dy/180*R_earth
            xres = pi*dx*cos(pi*y_start/180.0)/180*R_earth
#             print(f"Target resolution: {xres:.2f}x{yres:.2f} m")

        # Sample list is a three dimensional list that contains all panoramas
        # belonging to the mini tile. The mini tiles are aranged as
        # [0-nx][0-ny].
        sample_list = [[] for i in range(nx)]
        for i in range(nx):
            sample_list[i] = [[] for i in range(ny)]

        # Fill the sample list using the coordinates in the meta data.
        for i, meta in enumerate(self.meta_data):
            x = meta["geometry"]["coordinates"][0]
            y = meta["geometry"]["coordinates"][1]
            ix = int((x-x_start)/dx)
            iy = int((y-y_start)/dy)
            if ix >= 0 and ix < nx and iy >= 0 and iy < ny:
                sample_list[ix][iy].append(i)

        # Go through all the mini tiles and select the ones closest to
        # the corner of their mini tile.
        load_ids = []
        min_dist = [-1]
        for ix in range(nx):
            for iy in range(ny):
                cur_list = sample_list[ix][iy]
                # If there is nothing in the mini tile, skip.
                if not len(cur_list):
                    continue
                min_dist[0] = 10.0**10
                idx_min = -1

                # Compute the base points of the mini tile (southwest corner).
                x_base = x_start + dx*ix
                y_base = y_start + dy*iy
                y_fac, x_fac = degree_to_meter(y_base)
                # Compute minimum distance correcting lattitude.
                for i_meta in cur_list:
                    meta = self.meta_data[i_meta]
                    x = meta["geometry"]["coordinates"][0]
                    y = meta["geometry"]["coordinates"][1]
                    dist = ((x-x_base)*x_fac)**2 + ((y-y_base)*y_fac)**2
                    if dist < min_dist[0]:
                        idx_min = i_meta
                        min_dist[0] = dist
                if all_years:
                    x_min = self.meta_data[idx_min]["geometry"]["coordinates"][0]
                    y_min = self.meta_data[idx_min]["geometry"]["coordinates"][1]
                    dt = get_time_from_str(self.meta_data[idx_min]["timestamp"])
                    year_min = dt.year

                    neighbors = get_close_neighbors(sample_list, 
                                                    ix, iy, x_min, y_min, year_min, x_fac,
                                                    y_fac, self.meta_data, max_range)
                    idx_min = [idx_min]
                    idx_min.extend(neighbors)
#                     print(y_min, x_min)

                load_ids.extend(idx_min)
#         exit()
        load_ids = np.array(load_ids)
        super(AdamPanoramaTile, self).load(load_ids=load_ids)

    def green_direct(self, prepare_only=False, get_kwargs={}, load_kwargs={},
                     seg_kwargs={}, green_kwargs={}):
        seg_id = self.seg_model.id()
        green_id = self.green_model.id(one_class=True)
        green_level_key = get_green_key(self.pano_class, seg_id, green_id,
                                        self.grid_level)
        green_fp = os.path.join(self.data_dir, green_level_key+".json")
        try:
            with open(green_fp, "r") as f:
                green_res = json.load(f)
        except FileNotFoundError:
            self.get(**get_kwargs)
            self.load(**load_kwargs)
            if prepare_only:
                self.download()
                return _empty_green_res()
#             if prepare_only:
#                 return _empty_green_res()
#             self.seg_analysis(**seg_kwargs)
            green_res = self.green_pipe(**green_kwargs)
            if len(green_res["green"]) > 0:
                with open(green_fp, "w") as f:
                    json.dump(green_res, f, indent=2)
        return green_res
