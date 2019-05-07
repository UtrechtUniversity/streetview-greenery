"""
data.amsterdam.nl panorama API
"""

import os
import json
import requests
import urllib.request

from utils.logger import MetaLogger
from models.deeplab import DeepLabModel, plot_segmentation
from greenery.segment_perc import VegetationPercentage


def _get_id(elem):
    return elem['pano_id']


class PanoramaManager(object):
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
                self.panoramas = json.load(f)
        else:
            print("Downloading list of pictures")
            try:
                response = requests.get(self.url, params=params)
            except requests.exceptions.RequestException:
                print("HTTP request failed.")
                print(response.status_code)
                return None
            response_dict = json.loads(response.content)
            self.panoramas.extend(response_dict["_embedded"]["panoramas"])

            while response_dict['_links']['next']['href'] is not None:
                try:
                    response = requests.get(
                        response_dict['_links']['next']['href'])
                except requests.RequestException:
                    print("HTTP request failed.")
                    print(response.status_code)
                    return None
                response_dict = json.loads(response.content)
                self.panoramas.extend(response_dict["_embedded"]["panoramas"])

            with open(meta_fp, "w") as f:
                json.dump(self.panoramas, f, indent=2)

            print(f"Found {len(self.panoramas)} pictures. ")

        self.panoramas.sort(key=_get_id)

    def download(self, dest_dir="data.amsterdam", stride=1):
        dest_dir = os.path.join(dest_dir, "pics")
        os.makedirs(dest_dir, exist_ok=True)
        i = -1
        for pano in self.panoramas:
            i += 1
            if (i % stride) != 0:
                continue
            pano_url = pano["_links"]["equirectangular_small"]["href"]
            filename = pano["pano_id"]+".jpg"
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
            if model_id not in logger.log_dict['segmentation']:
                seg_res = new_model.run(panorama_fp, **model_kwargs)
                logger.add_results(seg_res, results_id=model_id)

    def greenery_analysis(self, model=DeepLabModel,
                          greenery=VegetationPercentage, **model_kwargs):
        new_model = model(**model_kwargs)
        model_id = new_model.id()
        green_model = greenery()
        green_results = {
            "lat": [],
            "long": [],
            "green": [],
        }
        for i in range(len(self.files)):
            logger = self.meta_loggers[i]
            if model_id in logger.log_dict['segmentation']:
                if green_model.id() not in logger.log_dict["segmentation"][model_id]:
                    seg_res = logger.log_dict['segmentation'][model_id]
                    my_green = green_model.test(seg_results=seg_res)
                    logger.add_greenery(my_green, model_id, green_model.id())
                else:
                    my_green = logger.log_dict["segmentation"][model_id][green_model.id()]
                green_results['green'].append(my_green)
                green_results['lat'].append(logger.log_dict['meta_data']['geometry']['coordinates'][1])
                green_results['long'].append(logger.log_dict['meta_data']['geometry']['coordinates'][0])
        return green_results

    def save(self):
        for logger in self.meta_loggers:
            logger.save()

    def show(self, model=DeepLabModel):
        model_id = model().id()
        for logger in self.meta_loggers:
            seg_map = logger.log_dict['segmentation'][model_id]['seg_map']
            color_map = logger.log_dict['segmentation'][model_id]['color_map']
            plot_segmentation(logger.panorama_fp, seg_map, color_map)

    def print_ids(self):
        for pano in self.panoramas:
            print(pano["pano_id"])

    def file_names(self):
        return self.files
