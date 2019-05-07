#!/usr/bin/env python

from API import AdamPanoramaManager
from models import DeepLabModel
from greenery.segment_perc import VegetationPercentage, plot_greenery


def main():
    panoramas = AdamPanoramaManager(seg_model=DeepLabModel,
                                    green_model=VegetationPercentage)
    cc = [52.299584, 4.971973]
    radius = 250  # meters
    panoramas.get()
    panoramas.load(n_sample=500)
    panoramas.seg_analysis()
    green_res = panoramas.green_analysis()
    plot_greenery(green_res)


if __name__ == "__main__":
    main()
