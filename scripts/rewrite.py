#!/usr/bin/env python

from pathlib import Path
from pprint import pprint

from greenstreet import TileManager
from greenstreet.API.base.tile import Tile
from tqdm import tqdm
from greenstreet.API.base.tile_manager import summarize_jobs
from greenstreet.utils.mapping import MapImageOverlay, create_map, compute_alpha

if __name__ == "__main__":
    base_data_dir = "../../output/oosterpark"
    tile_man = TileManager(base_data_dir, bbox_str="oosterpark",
                           grid_level=4, use_panorama=True,
                           weighted_panorama=True)
#     print(len(tile_man.tile_list))
#     tile_name = tile_man.tile_list[0]["name"]
#     bbox = tile_man.tile_list[0]["bbox"]
#     query = tile_man.tile_list[0]["query"]
#     tile = Tile(tile_name, bbox, Path(tile_man.tiles_dir, tile_name))
#     jobs = tile.get_jobs(tile_man.job_runner, query)
    jobs = tile_man.get_jobs()
    summarize_jobs(jobs)
    tile_man.execute(jobs)
    var, results = tile_man.compute_semivariance()
    tile_man.compute_krige(var, results)

    krige_dir = tile_man.get_krige_dir()
    map = MapImageOverlay.from_krige_dir(krige_dir)
    create_map(map, Path(krige_dir, "index.html"))
#     pprint(jobs)
#     tile.prepare(jobs)
# 
#     results = {}
#     for pano_id, job in tqdm(jobs.items()):
#         ret = tile_man.job_runner.execute(job)
#         print(ret)
#         results[pano_id] = ret
# 
#     tile.submit_result(jobs, results, tile_man.job_runner, query)
#     tile.save()
# 
#     pprint(tile.tile_data)
#     pprint(tile.result_data)
# #         pprint(ret)
#     if len(jobs["download"]):
#         for job in tqdm(jobs["download"]):
#             tile_man.job_runner.execute(**job)
#     for name, subs in jobs.items():
#         print(name, len(subs))
#     print(tile.get_pano_ids(query))
