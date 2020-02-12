import os
import json
from math import cos, pi, ceil, floor
from json.decoder import JSONDecodeError

from tqdm import tqdm
import numpy as np

from greenstreet.greenery.visualization import krige_greenery
from greenstreet.greenery.visualization import _alpha_from_coordinates
from greenstreet.greenery.visualization import _semivariance
from greenstreet.utils.mapping import MapImageOverlay
from greenstreet.utils import _empty_green_res, _extend_green_res
from greenstreet.utils.selection import select_bbox, get_segmentation_model,\
    get_green_model, get_job_runner
from greenstreet.sqlock import SQLiteLock
from greenstreet.query import GridQuery
from greenstreet.meta import AdamMetaData
from os.path import isfile


class TileManager(object):
    def __init__(self, data_dir, bbox_str="amsterdam",
                 grid_level=0, tile_resolution=1024,
                 seg_model_name='deeplab-mobilenet',
                 green_measure='vegetation',
                 all_years=False, use_panorama=False,
                 weighted_panorama=True,
                 data_source="adam", ):

        self.data_dir = data_dir
        bbox = select_bbox(bbox_str)
        self.tile_list = compute_tiles(bbox, tile_resolution)

        self.tiles_dir = os.path.join(data_dir, "tiles")
        self.cache_dir = os.path.join(data_dir, "cache")
        self.lock_fp = os.path.join(self.cache_dir, "lock.db")
        self.empty_fp = os.path.join(self.cache_dir, "empty_tiles.json")
        self.empty_files = load_empty_list(self.empty_fp, self.lock_fp)

        self.grid_level = grid_level
        self.all_years = all_years
        self.use_panorama = use_panorama
        self.data_source = data_source
        self.green_measure = green_measure
        self.green_mat = None
        self.all_green_res = None

        self.seg_model = get_segmentation_model(seg_model_name)
        self.green_model = get_green_model(use_panorama, weighted_panorama)
        self.job_runner = get_job_runner(
            use_panorama=use_panorama,
            seg_model=self.seg_model,
            green_model=self.green_model)

#         self.map_key = get_green_key(
#             data_source=data_source,
#             green_measure=green_measure,
#             seg_model=model,
#             use_panorama=use_panorama,
#             grid_level=grid_level,
#             all_years=all_years)
        self.initialize_tiles()
        self.pano_ids = None

    def initialize_tiles(self):
        for tile_data in self.tile_list.reshape(-1):
            tile_data["query"] = GridQuery(
                bbox=tile_data["bbox"], grid_level=self.grid_level)

    def get_meta_data(self):
        for tile_data in self.tile_list.reshape(-1):
            if "meta" in tile_data:
                continue
            param = tile_data["query"].param
            meta_fp = os.path.join(self.tiles_dir, tile_data["name"],
                                   "meta.json")
            try:
                tile_data["meta"] = AdamMetaData.from_file(meta_fp)
            except FileNotFoundError:
                tile_data["meta"] = AdamMetaData.from_download(param)
                os.makedirs(os.path.dirname(meta_fp), exist_ok=True)
                tile_data["meta"].to_file(meta_fp)

    def query(self):
        if self.pano_ids is not None:
            return self.pano_ids
        self.pano_ids = {}
        self.get_meta_data()
        for tile_data in self.tile_list.reshape(-1):
            pano_ids = tile_data["query"].sample_panoramas(tile_data["meta"])
            self.pano_ids.update({pano_id: tile_data for pano_id in pano_ids})
        return self.pano_ids

    def meta_summary(self):
        total_pictures = 0
        avail_pictures = 0
        for tile_data in self.tile_list.reshape(-1):
            tile = tile_data["tile"]
            tile.get_meta_data()
            summary = tile.summmary()
            total_pictures += summary["n_pictures"]
            avail_pictures += summary["n_downloaded"]
            print(f"[{tile_data['global_id_x']}, {tile_data['global_id_y']}]: "
                  f"{summary['n_downloaded']}/{summary['n_pictures']} pictures"
                  f", last modified on: {summary['time_modified']}")
        print("--------------------------------------------------")
        print(f"{len(self.tile_list.reshape(-1))} tiles,"
              f" {avail_pictures}/{total_pictures} pictures")

    def download(self):
        pano_ids = self.query()
        jobs = [
            {
                "data_dir": _data_dir(self.tiles_dir, tile_data["name"], pano_id),
                "program": "download",
                "pano_id": pano_id,
            }
            for pano_id, tile_data in pano_ids.items()
        ]
        for job in jobs:
            meta_fp = os.path.join(job["data_dir"], "meta.json")
            pano_id = job.pop("pano_id")
            if not isfile(meta_fp):
                os.makedirs(job["data_dir"], exist_ok=True)
                tile_data = pano_ids[pano_id]
                tile_data["meta"].to_file(meta_fp, pano_id=pano_id)

            result = self.job_runner.execute(**job)

    def segmentation(self):
        pano_ids = self.query()
        jobs = [
            {
                "data_dir": _data_dir(self.tiles_dir, tile_data["name"], pano_id),
                "program": "segmentation",
            }
            for pano_id, tile_data in pano_ids.items()
        ]
        for job in jobs:
            result = self.job_runner.execute(**job)

    def greenery(self):
        pano_ids = self.query()

        jobs = [
            {
                "data_dir": _data_dir(self.tiles_dir, tile_data["name"], pano_id),
                "program": "greenery",
            }
            for pano_id, tile_data in pano_ids.items()
        ]
        for job in jobs:
            result = self.job_runner.execute(**job)
            print(result)

    def krige_map(self, window_range=1, overlay_name="greenery", upscale=2,
                  n_job=1, job_id=0, **kwargs):
        if self.green_mat is None:
            self.green_direct(**kwargs)

        tile_res = upscale*2**self.grid_level
        full_krige_map = np.zeros((
            tile_res*self.n_tiles_y,
            tile_res*self.n_tiles_x
            )
        )

        krige_dir = os.path.join("data.amsterdam", "krige",
                                 overlay_name + "-" + self.map_key)
        os.makedirs(krige_dir, exist_ok=True)
        vario_fp = os.path.join(krige_dir, "variogram.json")
        try:
            with open(vario_fp, "r") as fp:
                vario_kwargs = json.load(fp)
        except (FileNotFoundError, JSONDecodeError):
            vario_kwargs = _semivariance(self.green_mat, plot=False,
                                         variogram_model="exponential")
            with open(vario_fp, "w") as fp:
                json.dump(vario_kwargs, fp)

        pbar = tqdm(total=self.n_tiles_x*self.n_tiles_y)
        for iy, green_row in enumerate(self.green_mat):
            for ix, green_res in enumerate(green_row):
                pbar.update()
                if (iy*len(green_row)+ix) % n_job != job_id:
                    continue
                krige_fp = os.path.join(krige_dir,
                                        "krige_"+str(ix)+"_"+str(iy)+".json")
                try:
                    with open(krige_fp, "r") as fp:
                        krige = np.array(json.load(fp))
                except (FileNotFoundError, JSONDecodeError):
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
                            _extend_green_res(
                                krige_green_res, self.green_mat[niy][nix])
                    if (
                            len(krige_green_res) == 0 or
                            len(krige_green_res['green']) <= 1):
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
                        krige = krige_greenery(krige_green_res, lat_grid,
                                               long_grid,
                                               init_kwargs=vario_kwargs)
                    except ValueError:
                        krige = np.zeros((tile_res, tile_res))
                    with open(krige_fp, "w") as fp:
                        json.dump(krige.tolist(), fp)

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
                                  alpha_map=alpha_map, name=overlay_name,
                                  min_green=0.0, max_green=1.0,
                                  cmap="RdYlGn")
        return overlay, self.map_key

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
        " Get the image resolution. "
        res_x = self.n_tiles_x*2**self.grid_level
        res_y = self.n_tiles_y*2**self.grid_level
        return [res_x, res_y]


def _data_dir(tile_dir, tile_name, pano_id):
    return os.path.join(tile_dir, tile_name, "pics", pano_id)


def compute_tiles(bbox, tile_resolution):
    NL_bbox = [
        [50.803721015, 3.31497114423],
        [53.5104033474, 7.09205325687]
    ]

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

    tile_list = np.array([{} for _ in range(n_tiles_x*n_tiles_y)])

    for i_tile in range(n_tiles_x*n_tiles_y):
        local_x = (i_tile % n_tiles_x)
        local_y = (i_tile // n_tiles_x)
        global_x = i_min_x + local_x
        global_y = i_min_y + local_y

        bbox = [
            [y_start+global_y*dy, x_start+global_x*dx],
            [y_start+(global_y+1)*dy, x_start+(global_x+1)*dx]
        ]
        name = f"NL_tile_{tile_resolution}m_{global_y}_{global_x}"

        tile = tile_list[i_tile]
        tile["global_id_x"] = global_x
        tile["global_id_y"] = global_y
        tile["local_id_x"] = local_x
        tile["local_id_y"] = local_y
        tile["bbox"] = bbox
        tile["name"] = name
        tile["tile"] = None

    return tile_list


def load_empty_list(empty_fp, lock_file):
    with SQLiteLock(lock_file, lock_name=empty_fp, blocking=True):
        try:
            with open(empty_fp, "r") as fp:
                empty_tiles = json.load(fp)
        except FileNotFoundError:
            empty_tiles = {}
            with open(empty_fp, "w") as fp:
                json.dump(empty_tiles, fp)
    return empty_tiles


def update_empty_list(empty_fp, lock_file, new_entry):
    with SQLiteLock(lock_file, lock_name=empty_fp, blocking=True):
        with open(empty_fp, "r") as fp:
            empty_list = json.load(fp)
        empty_list[new_entry] = True
        with open(empty_fp, "w") as fp:
            json.dump(empty_list, empty_fp)
    return empty_fp
