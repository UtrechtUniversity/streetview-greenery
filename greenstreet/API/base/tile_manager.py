import os
import json
from math import cos, pi, ceil, floor
from json.decoder import JSONDecodeError
from os.path import isfile, join

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
from greenstreet.API.adam import AdamMetaData
from greenstreet.db import get_db
from greenstreet.greenery.measure import Measure, LinearMeasure
from pprint import pprint


class TileManager(object):
    def __init__(self, data_dir, bbox_str="amsterdam",
                 grid_level=0, tile_resolution=1024,
                 seg_model_name='deeplab-mobilenet',
                 green_measure='vegetation',
                 all_years=False, use_panorama=False,
                 weighted_panorama=True,
                 data_source="adam"):

        self.data_dir = data_dir
        bbox = select_bbox(bbox_str)
        self.tile_list = compute_tiles(bbox, tile_resolution)

        self.tiles_dir = os.path.join(data_dir, "tiles")
        self.cache_dir = os.path.join(data_dir, "cache")
        self.krige_dir = os.path.join(data_dir, "krige")
        self.db_fp = os.path.join(data_dir, "results.db")
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

        self.initialize_tiles()
        self.pano_ids = None

    def initialize_tiles(self):
        for tile_data in self.tile_list.reshape(-1):
            tile_data["query"] = GridQuery(
                bbox=tile_data["bbox"], grid_level=self.grid_level)

    def get_meta_data(self, tile_data):
        if "meta" in tile_data:
            return
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
        for tile_data in self.tile_list.reshape(-1):
            query_dir = join(self.tiles_dir, tile_data["name"], "queries")
            os.makedirs(query_dir, exist_ok=True)
            query_fp = join(query_dir, tile_data["query"].file_name)
            try:
                new_pano_ids = tile_data["query"].pano_ids_from_file(query_fp)
            except FileNotFoundError:
                self.get_meta_data(tile_data)
                new_pano_ids = tile_data["query"].sample_panoramas(
                    tile_data["meta"])
                tile_data["query"].to_file(query_fp, new_pano_ids)
            self.pano_ids.update(
                {pano_id: tile_data for pano_id in new_pano_ids})
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
                "data_dir": _data_dir(
                    self.tiles_dir, tile_data["name"], pano_id),
                "program": "download",
                "pano_id": pano_id,
            }
            for pano_id, tile_data in pano_ids.items()
        ]
        for job in jobs:
            meta_fp = os.path.join(job["data_dir"], "meta.json")
            pano_id = job.pop("pano_id")

            if not isfile(meta_fp):
                tile_data = pano_ids[pano_id]
                self.get_meta_data(tile_data)
                tile_data["meta"].to_file(meta_fp, pano_id=pano_id)

            self.job_runner.execute(**job)

    def segmentation(self):
        pano_ids = self.query()
        jobs = [
            {
                "data_dir": _data_dir(
                    self.tiles_dir, tile_data["name"], pano_id),
                "program": "segmentation",
            }
            for pano_id, tile_data in pano_ids.items()
        ]
        for job in jobs:
            self.job_runner.execute(**job)

    def greenery(self):
        pano_ids = self.query()

        jobs = [
            {
                "data_dir": _data_dir(
                    self.tiles_dir, tile_data["name"], pano_id),
                "program": "greenery",
            }
            for pano_id, tile_data in pano_ids.items()
        ]
        for job in jobs:
            self.job_runner.execute(**job)

    def compute_krige(self, measure=LinearMeasure(weights={"vegetation": 1}),
                      window_range=1, upscale=2):
        n_tiles_x = max([tile["local_id_x"] for tile in self.tile_list]) + 1
        n_tiles_y = max([tile["local_id_y"] for tile in self.tile_list]) + 1
        tile_mat = self.tile_list.reshape((n_tiles_y, n_tiles_x))
        jobs = compute_krige_jobs(tile_mat, self.krige_dir,
                                  self.tiles_dir,
                                  self.db_fp,
                                  window_range=window_range)
        pprint(jobs)
        db = get_db(self.db_fp)
        tile_names = [tile["name"] for tile in self.tile_list]
        pano_ids = get_tile_results(db, tile_names, self.grid_level)
#         print(get_tile_ids(db, tile_names))
#         pano_ids = get_tile_results(db, tile_names, grid_level)
        green_ids = get_green_ids(db, pano_ids, self.job_runner.name,
                                  self.job_runner.seg_model.name,
                                  self.job_runner.green_model.name)
        result_dict = result_from_green_ids(db, green_ids, measure)
        print(result_dict)

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
                    neighbors.append(tile_mat[niy][nix]["name"])
            jobs.append({"tile_name": tile_mat[iy][ix]["name"],
                         "neighbors": neighbors,
                         "krige_dir": krige_dir,
                         "tiles_dir": tiles_dir,
                         "db_file": db_fp,
                         "measure": measure})
    return jobs


def _data_dir(tile_dir, tile_name, pano_id):
    return os.path.join(tile_dir, tile_name, "pics", pano_id)


def get_tile_ids(db, tile_names):
    tile_ids = db.execute(
        "SELECT id, name FROM tile WHERE name IN ({tile_list})".format(
            tile_list=",".join(['?']*len(tile_names))),
        tile_names
    ).fetchall()
    return {row["name"]: row["id"] for row in tile_ids}


def get_tile_results(db, tile_names, grid_level):
    pano_ids = db.execute(
        "SELECT queries.pano_id FROM queries JOIN tile "
        "ON queries.tile_id = tile.id "
        f"AND queries.grid_level = {grid_level} "
        "AND tile.name IN ({tile_list})".format(
            tile_list=",".join(['?']*len(tile_names))),
        tile_names
    ).fetchall()
    return [item["pano_id"] for item in pano_ids]


def get_green_ids(db, pano_ids, pano_type, seg_type, green_type):
    green_ids = db.execute(
        "SELECT greenery.id, greenery.pano_id FROM (((greenery "
        "JOIN panorama_type ON greenery.pano_type_id = panorama_type.id "
        f"AND panorama_type.name = '{pano_type}') "
        "JOIN segment_type ON greenery.seg_type_id = segment_type.id "
        f"AND segment_type.name = '{seg_type}') "
        "JOIN green_type ON greenery.green_type_id = green_type.id "
        f"AND green_type.name = '{green_type}') "
        "WHERE greenery.pano_id IN ({pano_list})".format(
            pano_list=",".join(['?']*len(pano_ids))),
        pano_ids
    ).fetchall()
    return {item["id"]: item["pano_id"] for item in green_ids}


def result_from_green_ids(db, green_ids, measure):
    result_values = db.execute(
        "SELECT result.value, green_class.name, result.green_id "
        "FROM result JOIN green_class "
        "ON result.green_class_id = result.green_class_id "
        "AND green_class.name IN ({class_list})"
        "AND result.green_id IN ({green_list})".format(
            class_list=",".join(['?']*len(measure.classes)),
            green_list=",".join(['?']*len(green_ids))
        ),
        measure.classes + list(green_ids)
    ).fetchall()

    results = {}
    for result in result_values:
        green_id = result["green_id"]
        value = result["value"]
        green_class = result["name"]
        if green_id not in results:
            results[green_id] = {}
        results[green_id][green_class] = value

    measure_res = {green_ids[green_id]: measure.compute(val)
                   for green_id, val in results.items()}

#     print(list(measure_res))
    extras = db.execute(
        "SELECT id, pano_id "
        "FROM greenery "
        "WHERE id IN ({green_list})".format(
            green_list=",".join(['?']*len(measure_res))
        ),
        list(measure_res)
    ).fetchall()
#     print(dict(extras[0]))
    green_2_pano = {x["id"]: x["pano_id"] for x in extras}
    pano_2_green = {v: k for k, v in green_2_pano.items()}

    pano_res = db.execute(
        "SELECT panorama.id, panorama.name, tile.name AS tile_name, "
        "panorama.latitude, panorama.longitude "
        "FROM panorama JOIN tile "
        "ON panorama.tile_id = tile.id "
        "WHERE panorama.id IN ({id_list})".format(
            id_list=",".join(['?']*len(green_2_pano))
        ),
        list(green_2_pano.values())
    ).fetchall()
#     print(dict(pano_res[0]))
    pano_res = {r["id"]: {
                    "panorama_name": r["name"],
                    "tile_name": r["tile_name"],
                    "latitude": r["latitude"],
                    "longitude": r["longitude"]
                }
                for r in pano_res}

    res_by_tile = {}

    for pano_id, props in pano_res.items():
        tile_name = props["tile_name"]
        if tile_name not in res_by_tile:
            res_by_tile[tile_name] = {
                "latitude": [],
                "longitude": [],
                "pano_id": [],
                "greenery": [],
                }
        res_by_tile[tile_name]["latitude"].append(props["latitude"])
        res_by_tile[tile_name]["longitude"].append(props["longitude"])
        res_by_tile[tile_name]["pano_id"].append(props["panorama_name"])
        greenery = measure_res[pano_2_green[pano_id]]
        res_by_tile[tile_name]["greenery"].append(greenery)

    return res_by_tile
#     print(pano_res)
#     print(res_by_tile)
#     print(green_2_pano)
#     print(results)
#     for green_id in green_ids:
        

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
