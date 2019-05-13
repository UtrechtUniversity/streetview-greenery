#!/usr/bin/env python

from API import AdamPanoramaManager
from models import DeepLabModel
from greenery.segment_perc import VegetationPercentage, plot_greenery,\
    plot_green_krige


def main():
    do_all = True
    # Start up the panorama manager.
    panoramas = AdamPanoramaManager(seg_model=DeepLabModel,
                                    green_model=VegetationPercentage)
    if do_all:
        # Get the meta data for all pictures.
        panoramas.get()
        # Only download some sample of them.
        panoramas.load(n_sample=10000)

    else:
        # Set coordinates of center point.
        cc = [52.299584, 4.971973]  # Degrees lattitude, longitude
        # Radius of circle to download.
        radius = 100  # meters
        panoramas.get(center=cc, radius=radius)
        panoramas.load()

    # Do segmentation analysis for loaded panorama's.
    panoramas.seg_analysis()
    # Get greenery from segmentation analysis.
    green_res = panoramas.green_analysis()
    # Plot the kriged map of the greenery.
    plot_green_krige(green_res)


if __name__ == "__main__":
    main()
