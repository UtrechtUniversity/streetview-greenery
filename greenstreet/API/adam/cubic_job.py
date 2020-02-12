import os
from time import sleep

import urllib.request
from urllib.error import HTTPError

from greenstreet.config import STATUS_OK, STATUS_FAIL
from greenstreet.API.base.job import GreenJob


class AdamCubicJob(GreenJob):
    name = "adam-cubic"
    sides = {
        "front": "f",
        "back": "b",
        # "up": "u",  # Up direction is problematic for machine learning.
        # "down": "d",  # Down direction is not very useful.
        "left": "l",
        "right": "r",
    }

    def _download(self, meta_data, picture_dir, n_try=5, timeout=3):
        pano_urls = self.pano_urls(meta_data)
        panorama_files = {
            side: os.path.join(picture_dir, pano_file)
            for side, pano_file in self.panorama_files().items()
        }

        if all(os.path.exists(pano_fp) for pano_fp in panorama_files.values()):
            return STATUS_OK

        for side, pano_url in pano_urls.items():
            panorama_fp = panorama_files[side]
            side_downloaded = False
            for _ in range(n_try):
                try:
                    urllib.request.urlretrieve(pano_url, panorama_fp)
                    side_downloaded = True
                except (ConnectionError, HTTPError):
                    sleep(timeout)
            if not side_downloaded:
                return STATUS_FAIL, "Failed to retrieve panorama from url."
        return STATUS_OK

    def _segmentation(self, model, data_dir):
        seg_res = {}
        panorama_fps = {side: os.path.join(data_dir, "pictures", pano_file)
                        for side, pano_file in self.panorama_files().items()}
        for side, panorama_fp in panorama_fps.items():
            seg_res[side] = model.run(panorama_fp)
        return seg_res

    def _greenery(self, seg_res, green_model):
        green_res_list = [
            green_model.transform(sub_seg_res)
            for sub_seg_res in seg_res.values()
        ]
        unique_names = []
        for green_res in green_res_list:
            unique_names.extend(list(green_res))
        unique_names = list(set(unique_names))
        green_res = {}
        for name in unique_names:
            cur_average = 0.0
            for sub_green_res in green_res_list:
                cur_average += sub_green_res.get(name, 0.0)
            green_res[name] = cur_average/len(green_res_list)
        return green_res

    def pano_urls(self, meta_data):
        base_url = meta_data["meta_data"]["cubic_img_baseurl"]
        return {
            side: base_url + f"1/{abrev}/0/0.jpg"
            for side, abrev in self.sides.items()
        }

    def panorama_files(self):
        return {side: f"adam-cubic-{side}.jpg" for side in self.sides}
