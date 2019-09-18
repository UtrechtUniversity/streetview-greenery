
import json
import requests
import os

from API import AdamPanorama
from API.adam_panorama_cubic import AdamPanoramaCubic
from API.panorama_manager import BasePanoramaManager
from json.decoder import JSONDecodeError
from tqdm import tqdm
from time import sleep


def _convert_meta(meta_data):
    """ Remove some unneeded meta data and move the link.

    Arguments
    ---------
    meta_data: dict
        Original meta data from data.amsterdam API.

    Returns
    -------
    dict:
        Transformed meta data.
    """
    all_dict = []
    for meta in meta_data:
        new_dict = meta
        new_dict["equirectangular_url"] = new_dict["_links"][
            "equirectangular_small"]["href"]
        del new_dict["_links"]
        all_dict.append(new_dict)
    return all_dict


class AdamPanoramaManager(BasePanoramaManager):
    " Object for using the Amsterdam data API "

    def __init__(self, data_dir="data.amsterdam", cubic_pictures=True,
                 **kwargs):
        super(AdamPanoramaManager, self).__init__(data_dir=data_dir, **kwargs)
        self.url = "https://api.data.amsterdam.nl/panorama/panoramas/"
        if cubic_pictures:
            self.pano_class = AdamPanoramaCubic
        else:
            self.pano_class = AdamPanorama

    def request_meta(self, params):
        """ Get meta data from data.amsterdam.

        Arguments
        ---------
        params: dict
            Parameters to retrieve meta data (coordinates etc).

        Returns
        -------
        list:
            List of all meta-data.
        """
        meta_list = []

        MAX_TRIES = 10
        n_try = 0
        while n_try < MAX_TRIES:
            try:
                response = requests.get(self.url, params=params)
            except requests.exceptions.RequestException:
                print("HTTP request failed.")
                sleep(60)

            if response.status_code == 200:
                break
            else:
                print(
                    f"Error (data.amsterdam): HTTP status code:"
                    f" {response.status_code}"
                )
                sleep(60)
            n_try += 1

        if n_try == MAX_TRIES:
            raise ValueError("Error (data.amsterdam): Error retrieving meta"
                             " data.")

        # Try to load data into a dictionary.
        try:
            response_dict = json.loads(response.content)
        except JSONDecodeError:
            print("Error (data.amsterdam): response not in correct format.")
            raise ValueError(response.content)

        new_list = _convert_meta(response_dict["_embedded"]["panoramas"])
        meta_list.extend(new_list)

        while response_dict['_links']['next']['href'] is not None:
            n_try = 0
            while n_try < MAX_TRIES:
                try:
                    response = requests.get(
                        response_dict['_links']['next']['href'])
                    break
                except requests.RequestException:
                    print(f"Error (data.amsterdam) HTTP request failed.")
                    sleep(60)
                    n_try += 1
            if n_try == MAX_TRIES:
                raise ValueError(
                    f"HTTP request failed with code {response.status_code}"
                )
            response_dict = json.loads(response.content)
            new_list = _convert_meta(
                response_dict["_embedded"]["panoramas"])
            # Add new meta-data to list.
            meta_list.extend(new_list)
        return meta_list

    def _meta_request_file(self, params):
        " Create metadata filename from request parameters. "
        file_name = "meta"
        if len(params) == 0:
            return "all.json"
        for param in params:
            if param != "page_size":
                file_name += f"_{param}={params[param]}"
        file_name += ".json"
        return file_name

    def _request_params(self, center=None, radius=None, **kwargs):
        " Parse parameters to format for data.amsterdam API. "
        params = {
            'srid': 4326,
            'page_size': 2000,
        }
        if radius is not None and radius <= 250:
            params['newest_in_range'] = True

        if center is not None:
            params['near'] = str(center[1])+","+str(center[0])
            if radius is not None:
                params['radius'] = float(radius)
        params.update(kwargs)
        return params

    def new_panorama(self, meta_data, data_dir, **kwargs):
        data_dir = os.path.join(data_dir, meta_data['pano_id'])
        return self.pano_class(meta_data=meta_data, data_dir=data_dir,
                               **kwargs)
