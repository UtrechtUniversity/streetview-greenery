
import os
import urllib.request

import numpy as np

from models.deeplab import plot_segmentation
from API.base_panorama import BasePanorama
from API.idgen import get_green_key


def _corrected_fractions(seg_map, names):
    """ Compute the class percentages, and correct for the angle
        with cubic images.
        The renormalization factors depend on how far from the middle
        the pixels are. In the middle, the factor is 1, and away from that:
        f(dx, dy) = (dx**2 + dy**2)^{-3/2},
        where dx, dy in [-1, 1].

    Arguments:
    ----------
    seg_map: np.array
        2D Array with assigned classes (int).
    names: np.array, str
        Class names associated with the numbers of seg_map.
    """

    nclass = 200  # Maximum number of class, actual can be lower.
    ny = seg_map.shape[0]
    nx = seg_map.shape[1]
    seg_frac_dict = {}
    seg_frac = np.zeros(nclass)
    tot_frac = 0
    for iy in range(ny):
        dy = 2*iy/ny-1
        for ix in range(nx):
            # Compute the correction factor.
            dx = 2*ix/nx-1
            fac = (dx**2+dy**2+1)**-1.5
            seg_frac[seg_map[iy, ix]] += fac
            tot_frac += fac

    # Normalize the class percentages.
    for i in range(nclass):
        if seg_frac[i] > 0:
            seg_frac_dict[names[i]] = seg_frac[i]/tot_frac
    return seg_frac_dict


class AdamPanoramaCubic(BasePanorama):
    " Object for using the Amsterdam data API with equirectengular data. "
    def __init__(self, meta_data, data_src="data.amsterdam", data_dir=None):
        self.sides = {
            "front": "f",
            "back": "b",
            # "up": "u",  # Up direction is problematic for machine learning.
            # "down": "d",  # Down direction is not very useful.
            "left": "l",
            "right": "r",
        }

        if data_dir is None:
            data_dir = os.path.join(data_src, "pics")
        super(AdamPanoramaCubic, self).__init__(
            meta_data=meta_data,
            data_dir=data_dir,
            data_src=data_src,
        )
        self.segment_fp = os.path.join(self.data_dir, f"segments_cubic.json")

    def parse_meta(self, meta_data):
        " Get some universally used data. "
        self.meta_data = meta_data
        self.latitude = meta_data["geometry"]["coordinates"][1]
        self.longitude = meta_data["geometry"]["coordinates"][0]
        self.id = meta_data["pano_id"]
        self.timestamp = meta_data["timestamp"]

    def fp_from_meta(self, meta_data):
        " Generate the meta and picture filenames. "

        self.pano_url = {}
        self.panorama_dir = self.data_dir
        self.panorama_fp = {}
        self.meta_fp = os.path.join(self.data_dir, "meta_data.json")
        if not os.path.exists(self.panorama_dir):
            os.makedirs(self.panorama_dir)

        # Download the different sides of the cube meta+img.
        for side in self.sides:
            abrev = self.sides[side]
            self.pano_url[side] = meta_data["cubic_img_baseurl"]
            self.pano_url[side] += f"1/{abrev}/0/0.jpg"
            self.panorama_fp[side] = os.path.join(
                self.panorama_dir, side+".jpg")

    def download(self):
        for side in self.pano_url:
            if not os.path.exists(self.panorama_fp[side]):
#                 print(f"Downoading {self.panorama_fp[side]} from {self.pano_url[side]}")
                urllib.request.urlretrieve(self.pano_url[side],
                                           self.panorama_fp[side])

    def seg_analysis(self, seg_model, show=False, recalc=False):
        "Do segmentation analysis, if possible load from file."
        model_id = seg_model.id()

        self.load_segmentation(self.segment_fp)
        if len(self.all_seg_res) < 1:
            self.all_seg_res = self.seg_run(seg_model, show=show)
            self.save_segmentation(self.segment_fp)
        elif show:
            self.show()

    def seg_to_green(self, seg_res, green_model):
        n_pano = len(seg_res)
        seg_frac = {}
        # Iterate over all phot directions (left, right, etc.)
        for side in seg_res:
            side_seg_res = seg_res[side]
            seg_map = np.array(side_seg_res['seg_map'])
            names = np.array(side_seg_res['color_map'][0])
            new_frac = green_model.seg_fractions(seg_map, names)

            # Add the result to the average.
            for class_name in new_frac:
                if class_name in seg_frac:
                    seg_frac[class_name] += new_frac[class_name]/n_pano
                else:
                    seg_frac[class_name] = new_frac[class_name]/n_pano
        return seg_frac

    def green_analysis(self, seg_model, green_model):
        "Do greenery analysis. If possible load from file."
        self.green_fp = os.path.join(self.data_dir, "greenery.json")
        green_id = green_model.id()
        seg_id = seg_model.id()
        key = get_green_key(AdamPanoramaCubic, seg_id, green_id)
        self.load_greenery(self.green_fp)
        if key not in self.all_green_res:
            # If we have not loaded segmentation results, do so now.
            if len(self.all_seg_res) < 1:
                self.seg_analysis(seg_model)

            seg_frac = {}
            n_pano = len(self.all_seg_res)
            # Iterate over all phot directions (left, right, etc.)
            for name in self.all_seg_res:
                seg_res = self.all_seg_res[name]
                seg_map = np.array(seg_res['seg_map'])
                names = np.array(seg_res['color_map'][0])
                new_frac = green_model.seg_fractions(seg_map, names)

                # Add the result to the average.
                for class_name in new_frac:
                    if class_name in seg_frac:
                        seg_frac[class_name] += new_frac[class_name]/n_pano
                    else:
                        seg_frac[class_name] = new_frac[class_name]/n_pano
            self.all_green_res[key] = seg_frac
            self.save_greenery(self.green_fp)
        return green_model.test(self.all_green_res[key])

    def seg_run(self, model, show=False):
        " Do segmentation analysis on the picture. "

        seg_res = {}
        for side in self.panorama_fp:
            pano_fp = self.panorama_fp[side]
            new_seg_res = model.run(pano_fp)
            seg_res[side] = new_seg_res

        if show:
            self.show()

        return seg_res

    def show(self):
        " Plot the segmentation analysis. "
        for side in self.all_seg_res:
            pano_fp = self.panorama_fp[side]
            seg_res = self.all_seg_res[side]
            seg_map = np.array(seg_res['seg_map'])
            color_map = seg_res["color_map"]
            names = np.array(color_map[0])

            plot_labels = {}
            fractions = _corrected_fractions(seg_map, names)
            for name in fractions:
                if fractions[name] < 0.001:
                    continue
                name_id = np.where(names == name)[0][0]
                plot_labels[name_id] = fractions[name]
            plot_segmentation(pano_fp, seg_map, color_map,
                              plot_labels=plot_labels)
