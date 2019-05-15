#!/usr/bin/env python

from models import DeepLabModel
from greenery.segment_perc import VegetationPercentage, plot_green_krige
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
    plot_green_krige(green_res, html_file="muiderpoort.html")
#     plot_greenery(green_res, cmap="YlGn")


if __name__ == "__main__":
    main()
