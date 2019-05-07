#!/usr/bin/env python

from models import DeepLabModel
from greenery.segment_perc import VegetationPercentage, plot_greenery
from API import AdamPanoramaManager


def main():
    panoramas = AdamPanoramaManager(seg_model=DeepLabModel,
                                    green_model=VegetationPercentage)
    cc = [52.360224, 4.935102]
    radius = 250  # meters
    panoramas.get(center=cc, radius=radius)
    panoramas.load(n_sample=500)
    panoramas.seg_analysis()
    green_res = panoramas.green_analysis()
    plot_greenery(green_res)


if __name__ == "__main__":
    main()
