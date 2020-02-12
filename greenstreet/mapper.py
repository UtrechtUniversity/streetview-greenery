import json
import os

from greenstreet.utils.selection import select_bbox, get_segmentation_model
from greenstreet.utils.selection import get_green_model
from greenstreet.API import TileManager
from greenstreet.utils.mapping import create_map, green_res_to_shp


def compute_map(model='deeplab-mobilenet', greenery_measure='vegetation',
                n_job=1, job_id=0, bbox_str='amsterdam', grid_level=0,
                krige_only=False, skip_overlay=False, prepare_only=False,
                use_panorama=False, all_years=False):

    bbox = select_bbox(bbox_str)
    seg_kwargs = get_segmentation_model(model)
    green_kwargs = get_green_model(greenery_measure)  #  TODO: Fix
    cubic_pictures = not use_panorama

    krige_n_job = n_job
    krige_job_id = job_id
    if krige_only:
        n_job = 1
        job_id = 0

    tile_man = TileManager(bbox=bbox, grid_level=grid_level, n_job=n_job,
                           job_id=job_id, **seg_kwargs,
                           cubic_pictures=cubic_pictures,
                           all_years=all_years,
                           **green_kwargs)

    green_res = tile_man.green_direct(prepare_only=prepare_only)

    if prepare_only or skip_overlay:
        return

    overlay, key = tile_man.krige_map(overlay_name=bbox_str, n_job=krige_n_job,
                                      job_id=krige_job_id)
    print(overlay)
    if krige_n_job != 1:
        return
    out_dir = os.path.join("data.amsterdam", "maps", key)
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
