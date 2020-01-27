'''
Manager of a set of panoramas.
'''
from abc import ABC
import os
import json
import numpy as np
import inspect
import time
from urllib.error import HTTPError

from greenstreet.models import DeepLabModel
from greenstreet.greenery import ClassPercentage
from greenstreet.utils.mapping import _empty_green_res, _add_green_res


class BasePanoramaManager(ABC):
    " Base class for managing a data set of panoramas. "

    def __init__(self, seg_model=DeepLabModel, seg_kwargs={},
                 green_model=ClassPercentage, green_kwargs={},
                 data_id="unknown", data_dir="data.default"):
        self.meta_data = []
        self.panoramas = []
        self.data_dir = data_dir

        # seg_model can be an instance or the class itself.
        # Initialize a new object, if a class was passed.
        if inspect.isclass(seg_model):
            self.seg_model = seg_model(**seg_kwargs)
        else:
            self.seg_model = seg_model

        if inspect.isclass(green_model):
            self.green_model = green_model(**green_kwargs)
        else:
            self.green_model = green_model

        self.id = data_id

    def get(self, **request_kwargs):
        " Get meta data of the requested pictures. "
        data_dir = self.data_dir
        params = self._request_params(**request_kwargs)
        meta_file = self._meta_request_file(params)
        meta_fp = os.path.join(data_dir, meta_file)

        if os.path.exists(meta_fp):
            with open(meta_fp, "r") as f:
                self.meta_data = json.load(f)
        else:
            self.meta_data = self.request_meta(params)
            if len(self.meta_data) == 0:
                return

            if not os.path.exists(self.data_dir):
                os.makedirs(self.data_dir, exist_ok=True)
            with open(meta_fp, "w") as f:
                json.dump(self.meta_data, f, indent=2)

    def load(self, n_sample=None, load_ids=None, pbar=None):
        """ Download/read pictures.

        Arguments
        ---------
        n_sample: int
            Sample that number of pictures. If n_sample is None,
            download/load all panorama's.
        """
        n_panorama = len(self.meta_data)
        # Set the seed, so that we will get the same samples each time.
        if load_ids is None:
            if n_sample is None:
                load_ids = np.arange(n_panorama)
            else:
                np.random.seed(1283742)
                load_ids = np.random.choice(
                    n_panorama, n_sample, replace=False)

        if len(load_ids) == 0:
            return

        dest_dir = os.path.join(self.data_dir, "pics")
        os.makedirs(dest_dir, exist_ok=True)

        self.meta_data = [self.meta_data[i] for i in load_ids]
        for meta in self.meta_data:
            try:
                self.panoramas.append(self.new_panorama(
                    meta_data=meta, data_dir=dest_dir))
            except HTTPError:
                pass
            if pbar is not None:
                pbar.update()

    def download(self):
        "Download the "
        avail_panoramas = []
        while len(self.panoramas):
            panorama = self.panoramas.pop()
            n_try = 0
            while n_try < 5:
                try:
                    panorama.download()
                    avail_panoramas.append(panorama)
                    break
                except (ConnectionError, HTTPError) as _:
                    n_try += 1
                    time.sleep(3)
        self.panoramas = avail_panoramas

    def seg_analysis(self, pbar=None, **kwargs):
        " Do segmentation analysis. "
        for panorama in self.panoramas:
            panorama.seg_analysis(seg_model=self.seg_model, **kwargs)
            if pbar is not None:
                pbar.update()

    def green_analysis(self, pbar=None):
        """
        Do greenery analysis.

        Returns
        -------
        dict:
            Dictionary that contains greenery points at (lat,long).
        """
        green_dict = {
            'green': [],
            'lat': [],
            'long': [],
            'timestamp': [],
        }
#         print("Doing greenery analysis..")
        for panorama in self.panoramas:
            green_frac = panorama.green_analysis(seg_model=self.seg_model,
                                                 green_model=self.green_model)
            _add_green_res(green_dict, green_frac, panorama)
            if pbar is not None:
                pbar.update()
        return green_dict

    def green_pipe(self, pbar=None):
        """
        Do greenery analysis.

        Returns
        -------
        dict:
            Dictionary that contains greenery points at (lat,long).
        """
        green_dict = _empty_green_res()
        broken_fp = os.path.join(self.data_dir, "broken_links.json")
        try:
            with open(broken_fp, "r") as f:
                broken_links = json.load(f)
        except FileNotFoundError:
            broken_links = {}

        new_broken_links = False
#         print("Doing greenery analysis..")
        for panorama in self.panoramas:
            if panorama.id in broken_links:
                continue
            try:
                green_frac = panorama.green_pipe(seg_model=self.seg_model,
                                                 green_model=self.green_model)
                _add_green_res(green_dict, green_frac, panorama)
            except HTTPError:
                new_broken_links = True
                broken_links[panorama.id] = True
            if pbar is not None:
                pbar.update()
        if new_broken_links:
            with open(broken_fp, "w") as fp:
                json.dump(broken_links, fp)
        return green_dict
