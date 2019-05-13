
import json
import requests

from API import AdamPanorama
from API.panorama_manager import BasePanoramaManager
from json.decoder import JSONDecodeError
from tqdm import tqdm


def _convert_meta(meta_data):
    all_dict = []
    for meta in meta_data:
#         print(meta)
        new_dict = meta
        new_dict["equirectangular_url"] = new_dict["_links"][
            "equirectangular_small"]["href"]
        del new_dict["_links"]
        all_dict.append(new_dict)
    return all_dict


class AdamPanoramaManager(BasePanoramaManager):
    " Object for using the Amsterdam data API"

    def __init__(self, **kwargs):
        super(AdamPanoramaManager, self).__init__(**kwargs)
        self.data_dir = "data.amsterdam"
        self.url = "https://api.data.amsterdam.nl/panorama/panoramas/"

    def request_meta(self, params):
        meta_list = []
        print("Downloading list of pictures")
        try:
            response = requests.get(self.url, params=params)
        except requests.exceptions.RequestException:
            print("HTTP request failed.")
            print(response.status_code)
            return None

        if response.status_code != 200:
            print(f"Error (data.amsterdam): HTTP status code:"
                  f" {response.status_code}")
            raise ValueError("Ouch")

        try:
            response_dict = json.loads(response.content)
        except JSONDecodeError:
            print("Error (data.amsterdam): response not in correct format.")
            raise ValueError(response.content)

        new_list = _convert_meta(response_dict["_embedded"]["panoramas"])
        meta_list.extend(new_list)
        n_total = response_dict['count']
#         print(f"Found {n_total}")
        with tqdm(total=n_total) as pbar:
            pbar.update(params["page_size"])
            while response_dict['_links']['next']['href'] is not None:
                try:
                    response = requests.get(
                        response_dict['_links']['next']['href'])
                except requests.RequestException:
                    print("HTTP request failed.")
                    print(response.status_code)
                    return None
                response_dict = json.loads(response.content)
                new_list = _convert_meta(response_dict["_embedded"]["panoramas"])
                meta_list.extend(new_list)
                pbar.update(len(response_dict["_embedded"]["panoramas"]))
#         print(meta_list)
        return meta_list

    def _meta_request_file(self, params):
        file_name = "meta"
        if len(params) == 0:
            return "all.json"
        for param in params:
            if param != "page_size":
                file_name += f"_{param}={params[param]}"
        file_name += ".json"
        return file_name

    def _request_params(self, center=None, radius=None):
        params = {
            'srid': 4326,
            'page_size': 10000,
        }
        if radius is not None and radius <= 250:
            params['newest_in_range'] = True

        if center is not None:
            params['near'] = str(center[1])+","+str(center[0])
            if radius is not None:
                params['radius'] = float(radius)
        return params

    def new_panorama(self, **kwargs):
        return AdamPanorama(**kwargs)
