import json
import requests
from time import sleep
from json.decoder import JSONDecodeError
from datetime import datetime


class AdamMetaData():
    name = "adam"

    def __init__(self, param={}):
        self.meta_data = {}
        self.param = param
        self.meta_timestamp = str(datetime.now())

    def coordinates(self, idx=None):
        return self._get(_coordinate, idx=idx)

    def timestamps(self, idx=None):
        return self._get(_timestamp, idx=idx)

    def _get(self, extractor, idx=None):
        if idx is None:
            idx = list(self.meta_data)

        iterable = True
        if not isinstance(idx, list):
            idx = [idx]
            iterable = False

        coor_list = {i: extractor(self.meta_data[i]) for i in idx}

        if iterable:
            return coor_list
        return coor_list[idx[0]]

    @classmethod
    def from_file(cls, meta_fp):
        with open(meta_fp, "r") as fp:
            meta_dict = json.load(fp)
        meta = cls(param=meta_dict["param"])
        meta.meta_data = meta_dict["meta_data"]
        meta.meta_timestamp = meta_dict["timestamp"]
        return meta

    @classmethod
    def from_download(cls, param):
        url = "https://api.data.amsterdam.nl/panorama/panoramas/"
        meta_list = []

        param = _request_params(**param)
        MAX_TRIES = 10
        n_try = 0
        while n_try < MAX_TRIES:
            try:
                response = requests.get(url, params=param)
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
        meta_data = {meta["pano_id"]: meta for meta in meta_list}
        meta_instance = cls(param=param)
        meta_instance.meta_data = meta_data
        return meta_instance

    def param_str(self):
        param_str = [str(key) + "=" + str(value)
                     for key, value in self.param.items()]
        return "_".join(param_str) + ".json"

    def to_file(self, meta_fp, pano_id=None):
        if pano_id is None:
            meta_dict = {
                "name": self.name,
                "param": self.param,
                "meta_timestamp": str(self.meta_timestamp),
                "meta_data": self.meta_data
            }
        else:
            meta_dict = {
                "name": self.name,
                "meta_timestamp": str(self.meta_timestamp),
                "pano_timestamp": self.timestamps(pano_id),
                "latitude": self.coordinates(pano_id)[1],
                "longitude": self.coordinates(pano_id)[0],
                "pano_id": pano_id,
                "meta_data": self.meta_data[pano_id]
            }
        with open(meta_fp, "w") as fp:
            json.dump(meta_dict, fp)


def _request_params(center=None, radius=None, **kwargs):
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


def _coordinate(meta):
    return (meta["geometry"]["coordinates"][0],
            meta["geometry"]["coordinates"][1])


def _timestamp(meta):
    return meta["timestamp"]
