import os
import json
from math import cos, pi, ceil, floor

from tqdm import tqdm
import numpy as np

from API.adam_tile import AdamPanoramaTile
from models.deeplab import DeepLabModel
from greenery.greenery import VegetationPercentage
from greenery.visualization import krige_greenery, _alpha_from_coordinates
from utils.mapping import MapImageOverlay
from utils import _empty_green_res, _extend_green_res


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
                                     f"empty_tiles_{tile_resolution}m.json")
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
            self.tile_list.append((tile, ix-i_min_x, iy-i_min_y))

        self.grid_level = grid_level
        self.n_tiles_x = n_tiles_x
        self.n_tiles_y = n_tiles_y
        self.dx = dx
        self.dy = dy
        self.x_start = x_start + i_min_x*dx
        self.y_start = y_start + i_min_y*dy
        self.green_mat = None
        self.all_green_res = None

    def green_direct(self, load_kwargs={}, **kwargs):
        all_green_res = {
            "green": [],
            "lat": [],
            "long": [],
        }
        self.green_mat = [[] for _ in range(self.n_tiles_y)]
        for iy in range(len(self.green_mat)):
            self.green_mat[iy] = [{} for _ in range(self.n_tiles_x)]

        load_kwargs['grid_level'] = self.grid_level
        for _ in tqdm(range(len(self.tile_list))):
            tile, ix, iy = self.tile_list.pop(0)
            new_green_res = tile.green_direct(load_kwargs=load_kwargs,
                                              **kwargs)
            _extend_green_res(all_green_res, new_green_res)
            self.green_mat[iy][ix] = new_green_res
        self.all_green_res = all_green_res
        return all_green_res

    def krige_map(self, window_range=1, overlay_name="greenery", upscale=2,
                  **kwargs):
        if self.green_mat is None:
            self.green_direct(**kwargs)

        tile_res = upscale*2**self.grid_level
        full_krige_map = np.zeros((
            tile_res*self.n_tiles_y,
            tile_res*self.n_tiles_x
            )
        )

        pbar = tqdm(total=self.n_tiles_x*self.n_tiles_y)
        for iy, green_row in enumerate(self.green_mat):
            for ix, green_res in enumerate(green_row):
                pbar.update()
                krige_green_res = _empty_green_res()
                _extend_green_res(krige_green_res, green_res)
                for idx in range(-window_range, window_range+1):
                    nix = ix + idx
                    if nix < 0 or nix >= self.n_tiles_x:
                        continue
                    for idy in range(-window_range, window_range+1):
                        niy = iy + idy
                        if niy < 0 or niy >= self.n_tiles_y:
                            continue
                        _extend_green_res(krige_green_res, self.green_mat[niy][nix])
                if len(krige_green_res) == 0 or len(krige_green_res['green']) <= 1:
                    continue
                x_start = self.x_start + ix*self.dx
                x_end = x_start + self.dx
                y_start = self.y_start + iy*self.dy
                y_end = y_start + self.dy
                long_grid = np.linspace(x_start, x_end, tile_res,
                                        endpoint=False)
                lat_grid = np.linspace(y_start, y_end, tile_res,
                                       endpoint=False)
                try:
                    krige = krige_greenery(krige_green_res, lat_grid, long_grid)
                except ValueError:
                    pass

                full_krige_map[
                    iy*tile_res:(iy+1)*tile_res,
                    ix*tile_res:(ix+1)*tile_res
                    ] = krige
        pbar.close()
        full_long_grid = np.linspace(
            self.x_start, self.x_start+self.n_tiles_x*self.dx,
            tile_res*self.n_tiles_x, endpoint=False)
        full_lat_grid = np.linspace(
            self.y_start, self.y_start+self.n_tiles_y*self.dy,
            tile_res*self.n_tiles_y, endpoint=False)

        full_krige_map[full_krige_map < 0] = 0
        alpha_map = _alpha_from_coordinates(self.all_green_res, full_lat_grid,
                                            full_long_grid)
        overlay = MapImageOverlay(full_krige_map, lat_grid=full_lat_grid,
                                  long_grid=full_long_grid,
                                  alpha_map=alpha_map, name=overlay_name)
        return overlay

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
