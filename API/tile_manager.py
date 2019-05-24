import os
import json
from math import cos, pi, ceil, floor

from tqdm import tqdm

from API.adam_tile import AdamPanoramaTile
from models.deeplab import DeepLabModel
from greenery.greenery import VegetationPercentage


def _extend_green_res(g1, g2):
    for key in g1:
        g1[key].extend(g2[key])


class TileManager(object):
    def __init__(self, tile_resolution=1024, bbox=None, grid_level=1,
                 n_job=1, job_id=0, seg_model=DeepLabModel, seg_kwargs={},
                 green_model=VegetationPercentage, green_kwargs={},
                 **kwargs):
        NL_bbox = [
            [50.803721015, 3.31497114423],
            [53.5104033474, 7.09205325687]
        ]

        if bbox is None:
            bbox = NL_bbox

        x_start = NL_bbox[0][1]
        x_end = NL_bbox[1][1]
        y_start = NL_bbox[0][0]
        y_end = NL_bbox[1][0]

        R_earth = 6356e3  # Radius of the earth in meters
        dy_target = 180*tile_resolution/(R_earth*pi)
        dx_target = dy_target/cos(pi*(y_start+y_end)/360.0)

        nx = ceil((x_end-x_start)/dx_target)
        ny = ceil((y_end-y_start)/dy_target)

        dx = (x_end-x_start)/nx
        dy = (y_end-y_start)/ny

        i_min_x = floor((bbox[0][1]-x_start)/dx)
        i_max_x = ceil((bbox[1][1]-x_start)/dx)

        i_min_y = floor((bbox[0][0]-y_start)/dy)
        i_max_y = ceil((bbox[1][0]-y_start)/dy)

        n_tiles_x = i_max_x-i_min_x
        n_tiles_y = i_max_y-i_min_y

        self.tile_list = []
        self.seg_model = seg_model(**seg_kwargs)
        self.green_model = green_model(**green_kwargs)

        data_dir = os.path.join("data.amsterdam", "tiles")
        self.empty_fp = os.path.join(data_dir,
                                     f"empty_tiles_{tile_resolution}m")
        try:
            with open(self.empty_fp, "r") as f:
                self.empty_tiles = json.load(f)
        except FileNotFoundError:
            self.empty_tiles = {}

        for i_tile in range(n_tiles_x*n_tiles_y):
            if i_tile % n_job != job_id:
                continue
            iy = i_min_y + (i_tile // n_tiles_x)
            ix = i_min_x + (i_tile % n_tiles_x)

            cur_bbox = [
                [y_start+iy*dy, x_start+ix*dx],
                [y_start+(iy+1)*dy, x_start+(ix+1)*dx]
            ]
            tile_name = f"NL_tile_{tile_resolution}m_{iy}_{ix}"
            if tile_name in self.empty_tiles:
                continue

            tile = AdamPanoramaTile(
                tile_name=tile_name, bbox=cur_bbox,
                seg_model=self.seg_model, green_model=self.green_model,
                **kwargs)
            self.tile_list.append(tile)

        self.grid_level = grid_level
        self.n_tiles_x = n_tiles_x
        self.n_tiles_y = n_tiles_y
        self.dx = dx
        self.dy = dy

    def get(self, **kwargs):
        print("Obtaining meta data..")
        for tile in tqdm(self.tile_list):
            tile.get(**kwargs)
            if len(tile.meta_data) == 0:
                self.empty_tiles[tile.tile_name] = True
        with open(self.empty_fp, "w") as f:
            json.dump(self.empty_tiles, f, indent=2)

    def load(self, **kwargs):
        for tile in self.tile_list:
            if tile.tile_name not in self.empty_tiles:
                tile.load(grid_level=self.grid_level, **kwargs)

    def seg_analysis(self, **kwargs):
        for tile in self.tile_list:
            if tile.tile_name not in self.empty_tiles:
                tile.seg_analysis(**kwargs)

    def green_analysis(self, **kwargs):
        green_res = {
            "green": [],
            "lat": [],
            "long": [],
        }

        for tile in self.tile_list:
            if tile.tile_name not in self.empty_tiles:
                new_green_res = tile.green_analysis(**kwargs)
                _extend_green_res(green_res, new_green_res)
        return green_res

    def resolution(self):
        res_x = self.n_tiles_x*2**self.grid_level
        res_y = self.n_tiles_y*2**self.grid_level
        return [res_x, res_y]
