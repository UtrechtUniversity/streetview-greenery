import numpy as np

from greenstreet.utils.sun import degree_to_meter
from copy import deepcopy
import json


class GridQuery():
    name = "grid"

    def __init__(self, bbox, grid_level=0):
        self.bbox = deepcopy(bbox)
        # Use southwest - northeast bounding box definition.
        if self.bbox[0][0] > self.bbox[1][0]:
            self.bbox[1][0], self.bbox[0][0] = self.bbox[0][0], self.bbox[1][0]
        if self.bbox[0][1] > self.bbox[1][1]:
            self.bbox[1][1], self.bbox[0][1] = self.bbox[0][1], self.bbox[1][1]
        self.grid_level = grid_level

    @property
    def param(self):
        bb_string = str(self.bbox[0][1]) + "," + str(self.bbox[1][0]) + "," + \
            str(self.bbox[1][1]) + "," + str(self.bbox[0][0])
        return {"bbox": bb_string}

    def sample_panoramas(self, meta_data):
        # Grid level is similar to a zoom level.
        # nx: number of points in x-direction.
        nx = 2**self.grid_level
        ny = 2**self.grid_level

        # x <-> longitude, y <-> latitude
        x_start = self.bbox[0][1]
        x_end = self.bbox[1][1]
        y_start = self.bbox[0][0]
        y_end = self.bbox[1][0]

        # Difference in degrees between measure points.
        dx = (x_end-x_start)/nx
        dy = (y_end-y_start)/ny

        # Sample list is a three dimensional list that contains all panoramas
        # belonging to the mini tile. The mini tiles are aranged as
        # [0-nx][0-ny].
        mini_tile_list = np.empty((ny, nx), dtype=object)
        for iy, ix in np.ndindex(mini_tile_list.shape):
            mini_tile_list[iy][ix] = []

        # Fill the sample list using the coordinates in the meta data.
        coordinates = meta_data.coordinates()
        for pano_id, coor in coordinates.items():
            x, y = coor
            ix = int((x-x_start)/dx)
            iy = int((y-y_start)/dy)
            if ix >= 0 and ix < nx and iy >= 0 and iy < ny:
                mini_tile_list[ix][iy].append(pano_id)

        # Go through all the mini tiles and select the ones closest to
        # the corner of their mini tile.
        load_ids = []
        min_dist = [-1]
        for iy, ix in np.ndindex(mini_tile_list.shape):
            mini_tile = mini_tile_list[ix][iy]
            # If there is nothing in the mini tile, skip.
            if not len(mini_tile):
                continue
            min_dist[0] = 10.0**10
            idx_min = -1

            # Compute the base points of the mini tile (southwest corner).
            x_base = x_start + dx*ix
            y_base = y_start + dy*iy
            y_fac, x_fac = degree_to_meter(y_base)
            # Compute minimum distance correcting lattitude.
            for i_meta in mini_tile:
                x, y = coordinates[i_meta]
                dist = ((x-x_base)*x_fac)**2 + ((y-y_base)*y_fac)**2
                if dist < min_dist[0]:
                    idx_min = i_meta
                    min_dist[0] = dist

            load_ids.append(idx_min)

        return np.array(load_ids)

    def to_file(self, query_fp, pano_ids):
        with open(query_fp, "w") as f:
            json.dump({
                "query_type": self.name,
                "pano_ids": pano_ids.tolist(),
                "param": self.param,
                "grid_level": self.grid_level,
            }, f)

    def pano_ids_from_file(self, query_fp):
        with open(query_fp, "r") as f:
            query = json.load(f)

        return np.array(query["pano_ids"])

    @property
    def file_name(self):
        return f"{self.name}_lvl_{self.grid_level}.json"
