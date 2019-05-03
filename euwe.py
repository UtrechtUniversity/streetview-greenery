#!/usr/bin/env python

from API import PanoramaAmsterdam
from models import DeepLabModel
from greenery.segment_perc import VegetationPercentage, plot_greenery


def main():
    panoramas = PanoramaAmsterdam()
    cc = [52.362248, 4.882971]
    radius = 250  # meters
    panoramas.get(center=cc, radius=radius)
    panoramas.download(stride=1)
    panoramas.seg_analysis(model=DeepLabModel)
    green_res = panoramas.greenery_analysis(model=DeepLabModel, greenery=VegetationPercentage)
    panoramas.save()
    plot_greenery(green_res)


if __name__ == "__main__":
    main()
