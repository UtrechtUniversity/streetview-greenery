#!/usr/bin/env python

import sys

from utils.ndvi import tiff_to_overlay


def main():
    if len(sys.argv) < 3:
        print("Need two arguments: tiff filename (x2)")
        sys.exit()
#     print(f"Reading {sys.argv[1]}")
    overlay_1 = tiff_to_overlay(sys.argv[1])
    overlay_2 = tiff_to_overlay(sys.argv[2])
    overlay_1.compare(overlay_2)

if __name__ == "__main__":
    main()
