#!/usr/bin/env python

from pathlib import Path

from greenstreet import TileManager
from greenstreet.API.base.tile_manager import summarize_jobs
from greenstreet.utils.mapping import MapImageOverlay, create_map

if __name__ == "__main__":
    base_data_dir = "../../output/oosterpark"
    tile_man = TileManager.from_config("test.ini", base_data_dir)
    tile_man.to_config("test2.ini")
#     tile_man = TileManager(base_data_dir, bbox_str="oosterpark",
#                            grid_level=2, use_panorama=True,
#                            use_weighting=True)

#     tile_man.to_config("test.ini")
# 
#     jobs = tile_man.get_jobs()
#     summarize_jobs(jobs)
#     tile_man.execute(jobs)
#     var, results = tile_man.compute_semivariance()
#     tile_man.compute_krige(var, results)
# 
#     krige_dir = tile_man.get_krige_dir()
#     map_overlay = MapImageOverlay.from_krige_dir(krige_dir)
#     create_map(map_overlay, Path(krige_dir, "index.html"))
