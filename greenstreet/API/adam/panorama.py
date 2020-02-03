import os
from os.path import splitext
import urllib.request

from greenstreet.API.base.panorama import BasePanorama
from urllib.error import HTTPError
from time import sleep


def _meta_fp(panorama_fp):
    base_fp = splitext(panorama_fp)[0]
    return base_fp+"_meta"+".json"


class AdamPanorama(BasePanorama):
    " Object for using the Amsterdam data API with equirectengular data. "
    name = "adam-panorama"

    def __init__(self, meta_data, data_dir):
        self.data_dir = data_dir
        super(AdamPanorama, self).__init__(
            meta_data=meta_data,
        )
        os.makedirs(self.data_dir, exist_ok=True)

    def parse_meta_data(self, meta_data):
        " Get some universally used data. "
        self.meta_data = meta_data
        self.latitude = meta_data["geometry"]["coordinates"][1]
        self.longitude = meta_data["geometry"]["coordinates"][0]
        self.id = meta_data["pano_id"]
        self.timestamp = meta_data["timestamp"]
        self.pano_url = meta_data["equirectangular_url"]
        self.filename = self.name + ".jpg"
        self.panorama_fp = os.path.join(self.data_dir, self.filename)
        self.meta_fp = _meta_fp(self.panorama_fp)

    def compute_segmentation(self, model):
        " Do segmentation analysis on the picture. "
        return model.run(self.panorama_fp)

    def download(self, n_try=5, timeout=3):
        if os.path.exists(self.panorama_fp):
            self.is_downloaded = True
            return

        self.is_downloaded = False
        for _ in range(n_try):
            try:
                urllib.request.urlretrieve(self.pano_url, self.panorama_fp)
                self.is_downloaded = True
            except (ConnectionError, HTTPError):
                sleep(timeout)
            self.is_downloaded = True
        if not self.is_downloaded:
            raise HTTPError(404, f"Error downloading file from link "
                            f"{self.pano_url}")

    def seg_to_green(self, seg_res, green_model=None):
        return green_model.transform(seg_res[self.name])
