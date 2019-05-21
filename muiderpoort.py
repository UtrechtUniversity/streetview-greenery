#!/usr/bin/env python

from models import DeepLabModel
from greenery import VegetationPercentage, create_kriged_overlay
from API import AdamPanoramaManager


def main():
    panoramas = AdamPanoramaManager(seg_model=DeepLabModel,
                                    green_model=VegetationPercentage)
    cc = [52.360224, 4.935102]
    radius = 400  # meters
    panoramas.get(center=cc, radius=radius)
    panoramas.load()
    panoramas.seg_analysis()
    green_res = panoramas.green_analysis()
    create_kriged_overlay(green_res, html_file="muiderpoort.html")


if __name__ == "__main__":
    main()
