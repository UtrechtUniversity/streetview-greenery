import os
import json
from math import cos, pi, ceil, floor
from pathlib import Path

from tqdm import tqdm
import numpy as np

from greenstreet.greenery.kriging import krige_greenery
from greenstreet.utils.mapping import compute_alpha
from greenstreet.utils import _extend_green_res
from greenstreet.utils.selection import select_bbox, get_segmentation_model,\
    get_green_model, get_job_runner
from greenstreet.sqlock import SQLiteLock
from greenstreet.query import GridQuery
from greenstreet.greenery.measure import LinearMeasure
from greenstreet.greenery.semivariogram import _semivariance
from greenstreet.API.base.tile import Tile


class TileManager(object):
    def __init__(self, data_dir, bbox_str="amsterdam",
                 grid_level=0, tile_resolution=1024,
                 seg_model_name='deeplab-mobilenet',
                 green_measure='vegetation',
                 all_years=False, use_panorama=False,
                 weighted_panorama=True,
                 data_source="adam"):

        self.data_dir = data_dir
        self.bbox_str = bbox_str
        bbox = select_bbox(bbox_str)
        self.tile_list = compute_tiles(bbox, tile_resolution)

        self.tiles_dir = os.path.join(data_dir, "tiles")
        self.cache_dir = os.path.join(data_dir, "cache")
        self.krige_dir = os.path.join(data_dir, "krige")
        self.db_fp = os.path.join(data_dir, "results.db")
        self.lock_fp = os.path.join(self.cache_dir, "lock.db")
        self.empty_fp = os.path.join(self.cache_dir, "empty_tiles.json")
        self.empty_files = load_empty_list(self.empty_fp, self.lock_fp)

        self.measure = LinearMeasure(weights={"vegetation": 1})
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

        self.initialize_tiles()
        self.pano_ids = None

    def initialize_tiles(self):
        for tile_name, tile_data in self.tile_list.items():
            tile_data["tile"] = Tile(
                tile_name, tile_data["bbox"],
                Path(self.tiles_dir, tile_name),
            )
            tile_data["query"] = GridQuery(
                bbox=tile_data["bbox"], grid_level=self.grid_level)

    def get_jobs(self, job_type="greenery"):
        all_jobs = {}
        for tile_name, tile_data in self.tile_list.items():
            tile = tile_data["tile"]
            new_jobs = tile.get_jobs(self.job_runner, tile_data["query"],
                                     job_type=job_type)
            if len(new_jobs):
                all_jobs[tile_name] = new_jobs
        return all_jobs

    def execute(self, jobs):
        results = {}
        for tile_name, job_list in jobs.items():
            tile = self.tile_list[tile_name]["tile"]
            tile.prepare(job_list)

        n_jobs = np.sum([len(x) for x in jobs.values()])
        pbar = tqdm(total=n_jobs)
        for tile_name, job_list in jobs.items():
            results[tile_name] = {}
            for pano_id, job in job_list.items():
                results[tile_name][pano_id] = self.job_runner.execute(job)
                pbar.update(1)
        pbar.close()
        for tile_name, tile_data in self.tile_list.items():
            tile = tile_data["tile"]
            query = tile_data["query"]
            try:
                tile_jobs = jobs[tile_name]
            except KeyError:
                tile_jobs = {}
            try:
                tile_results = results[tile_name]
            except KeyError:
                tile_results = {}
            tile.submit_result(tile_jobs, tile_results,
                               self.job_runner,
                               query)
            tile.save()

    def get_results(self):
        results = {}
        for tile_name, tile_data in self.tile_list.items():
            tile = tile_data["tile"]
            cur_results = tile.get_results(self.job_runner, tile_data["query"])
            cur_results["data"] = self.measure.compute(cur_results["data"])
            results[tile_name] = cur_results
        return results

    def compute_krige(self, var_param, result_dict, window_range=1,
                      upscale=2):
        krige_dir = self.get_krige_dir()
#         print([tile_list[tile]["local_id_x"] for tile in self.tile_list])
        n_tiles_x = max([tile["local_id_x"] for tile in self.tile_list.values()]) + 1
        n_tiles_y = max([tile["local_id_y"] for tile in self.tile_list.values()]) + 1
        tile_mat = np.empty((n_tiles_y, n_tiles_x), dtype=object)
        for tile_name in self.tile_list:
            local_x = self.tile_list[tile_name]["local_id_x"]
            local_y = self.tile_list[tile_name]["local_id_y"]
            tile_mat[local_y, local_x] = tile_name
        jobs = compute_krige_jobs(tile_mat, krige_dir,
                                  self.tiles_dir,
                                  self.db_fp,
                                  window_range=window_range)

        measures_per_tl = 2**self.grid_level
        dots_per_tile = max(10, upscale*measures_per_tl)
        os.makedirs(krige_dir, exist_ok=True)
        for job in jobs:
            tile = self.tile_list[job["tile_name"]]
            krige = krige_greenery(result_dict, job["neighbors"], tile,
                                   init_kwargs=var_param,
                                   dots_per_tile=dots_per_tile)
            krige_result = {
                "data": krige.tolist(),
                "bbox": tile["bbox"],
                "tile_name": job["tile_name"]
            }
            krige_fp = Path(krige_dir, f"{job['tile_name']}.json")
            with open(krige_fp, "w") as f:
                json.dump(krige_result, f)

        min_tile = self.tile_list[tile_mat[0][0]]
        max_tile = self.tile_list[tile_mat[-1][-1]]
        lat_min = min_tile["bbox"][0][0]
        lat_max = max_tile["bbox"][1][0]
        long_min = min_tile["bbox"][0][1]
        long_max = max_tile["bbox"][1][1]

        lat_grid = np.linspace(lat_min, lat_max, n_tiles_y*dots_per_tile, endpoint=False)
        long_grid = np.linspace(long_min, long_max, n_tiles_y*dots_per_tile, endpoint=False)

        alpha = compute_alpha(result_dict, lat_grid, long_grid)
        alpha_fp = Path(krige_dir, "alpha.json")
        with open(alpha_fp, "w") as f:
            json.dump(alpha.tolist(), f)

        index_data = {
            "bbox": [[lat_min, long_min], [lat_max, long_max]],
            "lat_grid": lat_grid.tolist(),
            "long_grid": long_grid.tolist(),
            "tile_matrix": tile_mat.tolist(),
        }
        index_fp = Path(krige_dir, "index.json")
        with open(index_fp, "w") as f:
            json.dump(index_data, f)

    def get_krige_dir(self):
        measure_name = self.measure.name
        krige_dir = Path(self.krige_dir, f"{self.bbox_str}_lvl{self.grid_level}",
                         self.job_runner.name, measure_name)
        os.makedirs(krige_dir, exist_ok=True)
        return krige_dir

    def compute_semivariance(self, plot=False):
        results = self.get_results()
        krige_dir = self.get_krige_dir()
        variogram_fp = Path(krige_dir, "variogram.json")

        semi_param = _semivariance(self.tile_list, results, plot=plot)
        with open(variogram_fp, "w") as f:
            json.dump(semi_param, f)
        return semi_param, results

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


def compute_krige_jobs(tile_mat, krige_dir, tiles_dir, db_fp,
                       measure=LinearMeasure(weights={"vegetation": 1}),
                       window_range=2):
    jobs = []
    for ix in range(tile_mat.shape[1]):
        for iy in range(tile_mat.shape[0]):
            neighbors = []
            for idx in range(-window_range, window_range+1):
                nix = ix + idx
                if nix < 0 or nix >= tile_mat.shape[1]:
                    continue
                for idy in range(-window_range, window_range+1):
                    niy = iy + idy
                    if niy < 0 or niy >= tile_mat.shape[0]:
                        continue
                    neighbors.append(tile_mat[niy][nix])
            jobs.append({"tile_name": tile_mat[iy][ix],
                         "neighbors": neighbors,
                         "krige_dir": krige_dir,
                         "tiles_dir": tiles_dir,
                         "measure": measure})
    return jobs


def _data_dir(tile_dir, tile_name, pano_id):
    return os.path.join(tile_dir, tile_name, "pics", pano_id)

# 
# def get_tile_ids(db, tile_names):
#     tile_ids = db.execute(
#         "SELECT id, name FROM tile WHERE name IN ({tile_list})".format(
#             tile_list=",".join(['?']*len(tile_names))),
#         tile_names
#     ).fetchall()
#     return {row["name"]: row["id"] for row in tile_ids}
# 
# 
# def get_tile_results(db, tile_names, grid_level):
#     pano_ids = db.execute(
#         "SELECT queries.pano_id FROM queries JOIN tile "
#         "ON queries.tile_id = tile.id "
#         f"AND queries.grid_level = {grid_level} "
#         "AND tile.name IN ({tile_list})".format(
#             tile_list=",".join(['?']*len(tile_names))),
#         tile_names
#     ).fetchall()
#     return [item["pano_id"] for item in pano_ids]
# 
# 
# def get_green_ids(db, pano_ids, pano_type, seg_type, green_type):
#     green_ids = db.execute(
#         "SELECT greenery.id, greenery.pano_id FROM (((greenery "
#         "JOIN panorama_type ON greenery.pano_type_id = panorama_type.id "
#         f"AND panorama_type.name = '{pano_type}') "
#         "JOIN segment_type ON greenery.seg_type_id = segment_type.id "
#         f"AND segment_type.name = '{seg_type}') "
#         "JOIN green_type ON greenery.green_type_id = green_type.id "
#         f"AND green_type.name = '{green_type}') "
#         "WHERE greenery.pano_id IN ({pano_list})".format(
#             pano_list=",".join(['?']*len(pano_ids))),
#         pano_ids
#     ).fetchall()
#     return {item["id"]: item["pano_id"] for item in green_ids}
# 
# 
# def result_from_green_ids(db, green_ids, measure):
#     result_values = db.execute(
#         "SELECT result.value, green_class.name, result.green_id "
#         "FROM result JOIN green_class "
#         "ON result.green_class_id = result.green_class_id "
#         "AND green_class.name IN ({class_list})"
#         "AND result.green_id IN ({green_list})".format(
#             class_list=",".join(['?']*len(measure.classes)),
#             green_list=",".join(['?']*len(green_ids))
#         ),
#         measure.classes + list(green_ids)
#     ).fetchall()
# 
#     results = {}
#     for result in result_values:
#         green_id = result["green_id"]
#         value = result["value"]
#         green_class = result["name"]
#         if green_id not in results:
#             results[green_id] = {}
#         results[green_id][green_class] = value
# 
# #     pprint(results)
#     measure_res = {green_id: measure.compute(val)
#                    for green_id, val in results.items()}
# 
# #     pprint(measure_res)
# 
#     pano_2_green = {v: k for k, v in green_ids.items()}
# 
#     pano_res = db.execute(
#         "SELECT panorama.id, panorama.name, tile.name AS tile_name, "
#         "panorama.latitude, panorama.longitude "
#         "FROM panorama JOIN tile "
#         "ON panorama.tile_id = tile.id "
#         "WHERE panorama.id IN ({id_list})".format(
#             id_list=",".join(['?']*len(green_ids))
#         ),
#         list(green_ids.values())
#     ).fetchall()
# 
#     pano_res = {r["id"]: {
#                     "panorama_name": r["name"],
#                     "tile_name": r["tile_name"],
#                     "latitude": r["latitude"],
#                     "longitude": r["longitude"]
#                 }
#                 for r in pano_res}
# 
# #     pprint(pano_res)
#     res_by_tile = {}
# 
#     for pano_id, props in pano_res.items():
#         tile_name = props["tile_name"]
#         if tile_name not in res_by_tile:
#             res_by_tile[tile_name] = {
#                 "latitude": [],
#                 "longitude": [],
#                 "pano_id": [],
#                 "greenery": [],
#                 }
#         res_by_tile[tile_name]["latitude"].append(props["latitude"])
#         res_by_tile[tile_name]["longitude"].append(props["longitude"])
#         res_by_tile[tile_name]["pano_id"].append(props["panorama_name"])
#         greenery = measure_res[pano_2_green[pano_id]]
#         res_by_tile[tile_name]["greenery"].append(greenery)
# 
#     return res_by_tile


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

#     tile_list = np.array([{} for _ in range(n_tiles_x*n_tiles_y)])

    tile_list = {}

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

        tile = {}
        tile["i_tile"] = i_tile
        tile["global_id_x"] = global_x
        tile["global_id_y"] = global_y
        tile["local_id_x"] = local_x
        tile["local_id_y"] = local_y
        tile["bbox"] = bbox
#         tile["name"] = name
        tile["tile"] = None
        tile_list[name] = tile

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


def summarize_jobs(jobs):
    n_tiles = len(jobs)
    n_jobs = {"download": 0, "segmentation": 0, "greenery": 0}
    for job in jobs.values():
        for pipe in job.values():
            for sub in pipe:
                n_jobs[sub["program"]] += 1
    return n_jobs