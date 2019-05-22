#!/usr/bin/env python
'''
Created on 22 May 2019

@author: qubix
'''

import sys
import argparse

def main():
    parser = argument_parser()
    args = parser.parse_args(sys.argv[1:])
    
    print(vars(args))

def argument_parser():
    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description="Mapping of greenery from street level imagery."
    )
    
    parser.add_argument(
        "-m", "--model",
        type=str,
        default="deeplab-mobilenet",
        help="Machine learning model for segmentation of images. "\
             "Default: 'deeplabe-mobilenet'"
    )
    parser.add_argument(
        "-g", "--greenery-measure",
        type=str,
        default="vegetation-perc",
        help="Greenery measure algorithm. Default: 'vegetation-perc' (only option)"
    )
    parser.add_argument(
        "-n", "--njobs",
        type=int,
        default=1,
        help="Spread the work out over this many jobs. Default: 1"
    )
    parser.add_argument(
        "-i", "--jobid",
        type=int,
        default=0,
        help="Id of the worker, should be in the range [0,njobs)."
    )
    parser.add_argument(
        "-b", "--bbox",
        type=str,
        default="amsterdam",
        help="Bounding box of the map to be made. Format: "\
             "'lat_SW,long_SW,lat_NE,long_NE'. Default: 'amsterdam'."
    )
    return parser


def compute_map(model='deeplab-mobilenet', greenery_measure='vegetation-perc',
                njobs=1, jobid=0, bbox='amsterdam'):
    

if __name__ == "__main__":
    main()
