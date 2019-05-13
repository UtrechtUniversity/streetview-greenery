#!/usr/bin/env python

from API import AdamPanoramaManager
from models import DeepLabModel
from greenery.segment_perc import VegetationPercentage, plot_greenery,\
    plot_green_krige


def main():
    do_all = True
    panoramas = AdamPanoramaManager(seg_model=DeepLabModel,
                                    green_model=VegetationPercentage)
    if do_all:
        panoramas.get()
        panoramas.load(n_sample=10000)

    else:
        cc = [52.299584, 4.971973]
        radius = 100  # meters
        panoramas.get(center=cc, radius=radius)
        panoramas.load()

    panoramas.seg_analysis()
    green_res = panoramas.green_analysis()
    plot_green_krige(green_res)


if __name__ == "__main__":
    main()
