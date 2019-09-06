#!/usr/bin/env python
'''
Created on 22 May 2019

@author: qubix
'''

import sys
import argparse
import os
import json


def main():
    parser = argument_parser()
    args = parser.parse_args(sys.argv[1:])
    compute_map(**vars(args))


def argument_parser():
    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description="Mapping of greenery from street level imagery."
    )
    parser.add_argument(
        "-m", "--model",
        type=str,
        default="deeplab-mobilenet",
        help="Machine learning model for segmentation of images. "
             "Default: 'deeplab-mobilenet'"
    )
    parser.add_argument(
        "-g", "--greenery-measure",
        type=str,
        default="vegetation",
        help="Greenery measure algorithm. "
             "Default: 'vegetation' "
             "Other options include {road, bus, sky, etc}."
    )
    parser.add_argument(
        "-n", "--njobs",
        type=int,
        default=1,
        dest="n_job",
        help="Spread the work out over this many jobs. Default: 1"
    )
    parser.add_argument(
        "-i", "--jobid",
        type=int,
        default=0,
        dest="job_id",
        help="Id of the worker, should be in the range [0,njobs)."
    )
    parser.add_argument(
        "-b", "--bbox",
        type=str,
        dest='bbox_str',
        default="amsterdam",
        help="Bounding box of the map to be made. Format: "
             "'lat_SW,long_SW,lat_NE,long_NE'. Default: 'amsterdam'."
    )
    parser.add_argument(
        "-l", "--grid-level",
        type=int,
        dest="grid_level",
        default=0,
        help="Set the detail of the grid, starting from 0 at a resolution of"
             " 1 per km, doubling the resolution by a factor of 2 for each"
             " level."
    )
    parser.add_argument(
        "--skip-overlay",
        default=False,
        dest="skip_overlay",
        action='store_true',
        help="Do not create a kriged overlayed map."
    )
    parser.add_argument(
        "--prepare",
        default=False,
        dest="prepare_only",
        action="store_true",
        help="Only prepare the data, do not compute anything."
    )
    parser.add_argument(
        "--panorama",
        default=False,
        dest="use_panorama",
        action="store_true",
        help="Use panorama pictures instead of cubic pictures"
    )
    parser.add_argument(
        "-y", "--historical-data",
        default=False,
        dest="all_years",
        action="store_true",
        help="Collect photos from every year within a small radius.",
    )
    parser.add_argument(
        "-k", "--parallel-krige",
        default=False,
        dest="krige_only",
        action="store_true",
        help="Only do the kriging in parallel; use if segmentation is there,"
             " but kriging not yet."
    )
    return parser


def compute_map(model='deeplab-mobilenet', greenery_measure='vegetation',
                n_job=1, job_id=0, bbox_str='amsterdam', grid_level=0,
                krige_only=False, skip_overlay=False, prepare_only=False,
                use_panorama=False, all_years=False):
    from utils.selection import select_bbox, select_seg_model
    from utils.selection import select_green_model
    from API.tile_manager import TileManager
    from utils.mapping import create_map, green_res_to_shp

    bbox = select_bbox(bbox_str)
    seg_kwargs = select_seg_model(model)
    green_kwargs = select_green_model(greenery_measure)
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


if __name__ == "__main__":
    main()
