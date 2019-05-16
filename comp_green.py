#!/usr/bin/env python

import os

import numpy as np

from API import AdamPanoramaManager
from utils.selection import select_area
import matplotlib.pyplot as plt
from models.deeplab import plot_segmentation
from greenery.segment_perc import plot_greenery, plot_green_krige
from utils.mapping import create_map


def main():
    area = "mijndenhof"
    if len(os.sys.argv) > 1:
        area = os.sys.argv[1]

    manager_kwargs, get_kwargs, load_kwargs = select_area(area, "mobilenet")
    panoramas_mob = AdamPanoramaManager(**manager_kwargs)
    panoramas_mob.get(**get_kwargs)
    panoramas_mob.load(**load_kwargs)
    panoramas_mob.seg_analysis()
    green_res_mob = panoramas_mob.green_analysis()

    manager_kwargs, get_kwargs, load_kwargs = select_area(area, "xception_71")
    panoramas_xpt = AdamPanoramaManager(**manager_kwargs)
    panoramas_xpt.get(**get_kwargs)
    panoramas_xpt.load(**load_kwargs)
    panoramas_xpt.seg_analysis()
    green_res_xcept65 = panoramas_xpt.green_analysis()

    x = np.arange(0, 0.53, 0.01)
    plt.scatter(green_res_xcept65["green"], green_res_mob["green"])
    plt.plot(x, x)
    plt.show()

    mob_overlay = plot_green_krige(green_res_mob, name="mobilenet",
                                   overlay_fp="krige_mob.json")
    xcept_overlay = plot_green_krige(green_res_xcept65, name="xception71",
                                     overlay_fp="krige_xception71.json")
    print(mob_overlay.name)
    print(xcept_overlay.name)
    map_fp = "green_comp.html"
    create_map([mob_overlay, xcept_overlay], map_fp)

#     for i in range(len(panoramas_mob.panoramas)):
#         pano_mob = panoramas_mob.panoramas[i]
#         pano_xpt = panoramas_xpt.panoramas[i]
#         plot_segmentation(pano_mob.panorama_fp, **pano_mob.seg_res, show=False)
#         plot_segmentation(pano_xpt.panorama_fp, **pano_xpt.seg_res, show=True)


if __name__ == "__main__":
    main()
