import os
from time import sleep

import urllib.request
from urllib.error import HTTPError

from greenstreet.config import STATUS_OK, STATUS_FAIL
from greenstreet.API.base.job import GreenJob


class AdamPanoramaJob(GreenJob):
    name = "adam-panorama"

    def _download(self, meta_data, picture_dir, n_try=5, timeout=3):
        panorama_fp = os.path.join(picture_dir, "adam-panorama.jpg")
        pano_url = meta_data["meta_data"]["equirectangular_url"]

        if os.path.exists(panorama_fp):
            return STATUS_OK

        for _ in range(n_try):
            try:
                urllib.request.urlretrieve(pano_url, panorama_fp)
                return STATUS_OK
            except (ConnectionError, HTTPError):
                sleep(timeout)
        return STATUS_FAIL, "Failed to retrieve panorama from url."

    def _segmentation(self, model, data_dir):
        panorama_fp = os.path.join(data_dir, "pictures", "adam-panorama.jpg")
        return {"panorama": model.run(panorama_fp)}

    def _greenery(self, seg_res, green_model):
        return green_model.transform(seg_res["panorama"])
