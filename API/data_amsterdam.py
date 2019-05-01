"""
data.amsterdam.nl panorama API
"""

import os
import json
import requests
import urllib.request


def get_id(elem):
    return elem['pano_id']


class PanoramaAmsterdam(object):
    " Object for using the Amsterdam data API"

    def __init__(self):
        self.url = "https://api.data.amsterdam.nl/panorama/panoramas/"
        self.panoramas = []

    def get(self, center=None, radius=None):
        params = {
            'srid': 4326,
            'newest_in_range': True,
        }

        if center is not None:
            params['near'] = str(center[1])+","+str(center[0])
            if radius is not None:
                params['radius'] = float(radius)

        try:
            response = requests.get(self.url, params=params)
        except requests.exceptions.RequestException:
            print("HTTP request failed.")
            print(response.status_code)
            return None

        response_dict = json.loads(response.content)
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
        self.panoramas.sort(key=get_id)

    def download(self, dest_dir="data.amsterdam"):
        dest_dir = os.path.join(dest_dir, "pics")
        os.makedirs(dest_dir, exist_ok=True)
        for pano in self.panoramas:
            pano_url = pano["_links"]["equirectangular_small"]["href"]
            filename = pano["filename"]
            dest_fp = os.path.join(dest_dir, filename)
            if not os.path.isfile(dest_fp):
                urllib.request.urlretrieve(pano_url, dest_fp)

    def print_ids(self):
        for pano in self.panoramas:
            print(pano["pano_id"])
