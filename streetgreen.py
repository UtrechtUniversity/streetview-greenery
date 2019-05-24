#!/usr/bin/env python
'''
Created on 22 May 2019

@author: qubix
'''

import sys
import argparse
import os

from utils.selection import select_bbox, select_seg_model, select_green_model
from API.tile_manager import TileManager
from greenery.visualization import plot_greenery, create_kriged_overlay
from utils.mapping import create_map
from os.path import splitext


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
        default="vegetation_perc",
        help="Greenery measure algorithm. "
             "Default: 'vegetation_perc' (only option)"
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
    return parser


def compute_map(model='deeplab-mobilenet', greenery_measure='vegetation_perc',
                n_job=1, job_id=0, bbox_str='amsterdam', grid_level=0,
                skip_overlay=False, prepare_only=False):
    bbox = select_bbox(bbox_str)
    seg_kwargs = select_seg_model(model)
    green_kwargs = select_green_model(greenery_measure)

    tile_man = TileManager(bbox=bbox, grid_level=grid_level, n_job=n_job,
                           job_id=job_id, **seg_kwargs, **green_kwargs)
    tile_man.get()
    tile_man.load()

    if prepare_only:
        return

    tile_man.seg_analysis()
    green_res = tile_man.green_analysis()

    if skip_overlay:
        return

    overlay_dir = os.path.join("data.amsterdam", "maps")
    overlay_file = f"krige_{bbox_str}_level={grid_level}.json"
    overlay_fp = os.path.join(overlay_dir, overlay_file)
    os.makedirs(overlay_dir, exist_ok=True)

    res_mult = 2
    resolution = tile_man.resolution()
    resolution = [res_mult*x for x in resolution]

    overlay = create_kriged_overlay(green_res, overlay_fp=overlay_fp,
                                    grid=resolution)
    create_map([overlay], html_file=splitext(overlay_fp)[0]+".html")
#     plot_greenery(green_res)


if __name__ == "__main__":
    main()
