"""
data.amsterdam.nl panorama API
"""

import os
import json
import requests
import urllib.request

from utils.logger import MetaLogger
from models.deeplab import DeepLabModel, plot_segmentation


def _get_id(elem):
    return elem['pano_id']


def _meta_request_file(params):
    file_name = "meta"
    if len(params) == 0:
        return "all.json"
    for param in params:
        file_name += f"_{param}={params[param]}"
    file_name += ".json"
    return file_name


class PanoramaAmsterdam(object):
    " Object for using the Amsterdam data API"

    def __init__(self):
        self.url = "https://api.data.amsterdam.nl/panorama/panoramas/"
        self.panoramas = []
        self.files = []
        self.meta_loggers = []

    def get(self, center=None, radius=None, meta_dir="data.amsterdam"):
        params = {
            'srid': 4326,
            'newest_in_range': True,
        }

        if center is not None:
            params['near'] = str(center[1])+","+str(center[0])
            if radius is not None:
                params['radius'] = float(radius)

        meta_fp = os.path.join(meta_dir, _meta_request_file(params))
        if os.path.exists(meta_fp):
            with open(meta_fp, "r") as f:
                response_dict = json.load(f)
        else:
            try:
                response = requests.get(self.url, params=params)
            except requests.exceptions.RequestException:
                print("HTTP request failed.")
                print(response.status_code)
                return None
            response_dict = json.loads(response.content)
            with open(meta_fp, "w") as f:
                json.dump(response_dict, f)

        self.panoramas = response_dict["_embedded"]["panoramas"]

        while response_dict['_links']['next']['href'] is not None:
            try:
                response = requests.get(response_dict['_links']['next']['href'])
            except requests.RequestException:
                print("HTTP request failed.")
                print(response.status_code)
                return None
            response_dict = json.loads(response.content)
            self.panoramas.extend(response_dict["_embedded"]["panoramas"])
        self.panoramas.sort(key=_get_id)

    def download(self, dest_dir="data.amsterdam"):
        dest_dir = os.path.join(dest_dir, "pics")
        os.makedirs(dest_dir, exist_ok=True)
        for pano in self.panoramas:
            pano_url = pano["_links"]["equirectangular_small"]["href"]
            filename = pano["filename"]
            dest_fp = os.path.join(dest_dir, filename)
            if not os.path.isfile(dest_fp):
                urllib.request.urlretrieve(pano_url, dest_fp)
            new_logger = MetaLogger(panorama_fp=dest_fp)
            new_logger.add_meta_data(meta_data=pano)
            self.meta_loggers.append(new_logger)
            self.files.append(dest_fp)

    def seg_analysis(self, model=DeepLabModel, **model_kwargs):
        new_model = model(**model_kwargs)
        model_id = new_model.id()
        for i in range(len(self.files)):
            panorama_fp = self.files[i]
            logger = self.meta_loggers[i]
            if model_id not in logger.log_dict['results']:
                seg_res = new_model.run(panorama_fp, **model_kwargs)
                logger.add_results(seg_res, results_id=model_id)

    def show(self, model=DeepLabModel):
        model_id = model().id()
        for logger in self.meta_loggers:
            seg_map = logger.log_dict['results'][model_id]['seg_map']
            color_map = logger.log_dict['results'][model_id]['color_map']
            plot_segmentation(logger.panorama_fp, seg_map, color_map)

    def print_ids(self):
        for pano in self.panoramas:
            print(pano["pano_id"])

    def file_names(self):
        return self.files
