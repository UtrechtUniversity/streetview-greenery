import json
import os
from pathlib import Path

from greenstreet.utils.selection import select_bbox, get_segmentation_model
from greenstreet.utils.selection import get_green_model
from greenstreet.API import TileManager
from greenstreet.API.base.tile_manager import summarize_jobs
from greenstreet.utils.mapping import create_map, green_res_to_shp


def compute_map(model='deeplab-mobilenet',
                greenery_measure='vegetation',
                n_job=1, job_id=0, bbox_str='amsterdam', grid_level=0,
                krige_only=False, skip_overlay=False, prepare_only=False,
                use_panorama=False, all_years=False,
                data_dir=None):

    if data_dir is None:
        data_dir = Path("data.amsterdam", bbox_str)

    krige_n_job = n_job
    krige_job_id = job_id
    if krige_only:
        n_job = 1
        job_id = 0

    tile_man = TileManager(bbox_str=bbox_str, grid_level=grid_level,
                           seg_model_name=model,
                           use_panorama=use_panorama,
                           green_weights={greenery_measure: 1},
                           data_dir=data_dir)

    jobs = tile_man.get_jobs()
    summarize_jobs(jobs)
    print(green_res)

    if prepare_only or skip_overlay:
        return

    overlay, key = tile_man.krige_map(overlay_name=bbox_str, n_job=krige_n_job,
                                      job_id=krige_job_id)
    print(overlay)
    if krige_n_job != 1:
        return
    out_dir = Path(data_dir, "maps", key)
    overlay_file = f"{bbox_str}.html"
    overlay_fp = os.path.join(out_dir, overlay_file)
    geo_tiff_fp = os.path.join(out_dir, f"{bbox_str}.tif")
    shape_fp = os.path.join(out_dir, f"{bbox_str}.shp")
    json_fp = os.path.join(out_dir, f"{bbox_str}.json")
    os.makedirs(out_dir, exist_ok=True)

    with open(json_fp, "w") as fp:
        json.dump(green_res, fp)
    create_map(overlay, html_file=overlay_fp)
    overlay.write_geotiff(geo_tiff_fp)

    green_res_to_shp(green_res, tile_man.green_model.id(one_class=True),
                     shape_fp)
