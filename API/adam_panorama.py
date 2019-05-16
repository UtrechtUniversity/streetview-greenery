import os
from os.path import splitext
import urllib.request
from API.base_panorama import BasePanorama
import numpy as np
from models.deeplab import plot_segmentation


def _meta_fp(panorama_fp):
    base_fp = splitext(panorama_fp)[0]
    return base_fp+"_meta"+".json"


class AdamPanorama(BasePanorama):
    " Object for using the Amsterdam data API with equirectengular data. "
    def __init__(self, meta_data, data_dir="data.amsterdam"):
        data_src = "data.amsterdam"
        data_dir = os.path.join(data_src, "pics")
        super(AdamPanorama, self).__init__(
            meta_data=meta_data,
            data_dir=data_dir,
            data_src=data_src,
        )
        self.seg_res = None

    def parse(self, meta_data):
        " Get some universally used data. "
        self.meta_data = meta_data
        self.latitude = meta_data["geometry"]["coordinates"][1]
        self.longitude = meta_data["geometry"]["coordinates"][0]
        self.id = meta_data["pano_id"]

    def fp_from_meta(self, meta_data):
        " Generate the meta and picture filenames. "
        self.pano_url = meta_data["equirectangular_url"]
        self.filename = meta_data["pano_id"]+".jpg"
        self.panorama_fp = os.path.join(self.data_dir, self.filename)
        self.meta_fp = _meta_fp(self.panorama_fp)
        if not os.path.exists(self.panorama_fp):
            urllib.request.urlretrieve(self.pano_url, self.panorama_fp)

    def seg_run(self, model, show=False):
        " Do segmentation analysis on the picture. "
        seg_res = model.run(self.panorama_fp)
        self.seg_res = seg_res

        seg_map = np.array(seg_res['seg_map'])
        names = np.array(seg_res['color_map'][0])

        unique, counts = np.unique(seg_map, return_counts=True, axis=None)

        fractions = counts/seg_map.size
        if show:
            plot_segmentation(self.panorama_fp, seg_map, seg_res["color_map"])
        return dict(zip(names[unique], fractions))
