
import sys
import argparse

from greenstreet.mapper import compute_map


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


