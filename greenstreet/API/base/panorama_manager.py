'''
Manager of a set of panoramas.
'''
from abc import ABC, abstractmethod
import os
import json
import numpy as np
from urllib.error import HTTPError

from greenstreet.models import DeepLabModel
from greenstreet.greenery import ClassPercentage
from greenstreet.data import GreenData


class BasePanoramaManager(ABC):
    "Base class for managing a data set of panoramas."

    def __init__(self, data_dir, seg_model=DeepLabModel(),
                 green_model=ClassPercentage(), n_sample=10):
        self.meta_data = None
        self.panoramas = []
        self.data_dir = data_dir
        self.cache_dir = os.path.join(data_dir, "cache")
        self.broken_link_fp = os.path.join(self.cache_dir, "broken_links.json")

        self.seg_model = seg_model
        self.green_model = green_model

        self.n_sample = n_sample

    @abstractmethod
    def _request_params(self):
        raise NotImplementedError

    @abstractmethod
    def _meta_request_file(self):
        raise NotImplementedError

    def id(self):
        return f"{self.green_model.id()}-{self.seg_model.id()}"

    def get_meta_data(self, **kwargs):
        " Get meta data of the requested pictures. "
        if self.meta_data is not None:
            return

        data_dir = self.data_dir
        params = self._request_params(**kwargs)
        meta_file = self._meta_request_file(params)
        meta_fp = os.path.join(data_dir, meta_file)
        self.meta_fp = meta_fp

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

    def sample_panoramas(self):
        """ Download/read pictures.

        Arguments
        ---------
        n_sample: int
            Sample that number of pictures. If n_sample is None,
            download/load all panorama's.
        """

        n_sample = self.n_sample
        np.random.seed(1283742)
        n_panorama = len(self.meta_data)
        sample_ids = np.random.choice(n_panorama, n_sample, replace=False)
        return sample_ids

    def initialize_panoramas(self, pbar=None):
        panorama_ids = self.sample_panoramas()

        dest_dir = os.path.join(self.data_dir, "pics")
        os.makedirs(dest_dir, exist_ok=True)

        self.panoramas = []
#         self.meta_data = [self.meta_data[i] for i in panorama_ids]
        for i in panorama_ids:
            meta = self.meta_data[i]
            new_panorama = self.new_panorama(data_dir=dest_dir, meta_data=meta)
            self.panoramas.append(new_panorama)

            if pbar is not None:
                pbar.update()

    def download(self):
        "Download the pictures."
        broken_links = get_meta_links(self.broken_link_fp)
        new_broken_links = {}
        self.get_meta_data()
        self.initialize_panoramas()
        avail_panoramas = []
        while len(self.panoramas):
            panorama = self.panoramas.pop()
            if panorama.id in broken_links:
                continue
            try:
                panorama.download()
                avail_panoramas.append(panorama)
            except HTTPError:
                new_broken_links[panorama.id] = True
        self.panoramas = avail_panoramas
        if len(new_broken_links) > 0:
            update_meta_links(self.broken_link_fp, new_broken_links)

    def segmentate(self, pbar=None, compute=True, pipe=True):
        " Do segmentation analysis. "
        broken_links = get_meta_links(self.broken_link_fp)
        new_broken_links = {}
        for panorama in self.panoramas:
            if panorama in broken_links:
                continue
            try:
                panorama.get_segmentation(
                    seg_model=self.seg_model, compute=compute, pipe=pipe)
            except HTTPError:
                new_broken_links[panorama.id] = True
            if pbar is not None:
                pbar.update()
        if len(new_broken_links) > 0:
            update_meta_links(self.broken_link_fp, new_broken_links)

    def get_greenery(self, pbar=None, compute=True, pipe=True):
        """
        Do greenery analysis.

        Returns
        -------
        dict:
            Dictionary that contains greenery points at (lat,long).
        """
        broken_links = get_meta_links(self.broken_link_fp)
        green_data = GreenData()
#         print("Doing greenery analysis..")
        new_broken_links = {}
        for panorama in self.panoramas:
            if panorama.id in broken_links:
                continue
            try:
                panorama.get_greenery(
                    seg_model=self.seg_model, green_model=self.green_model,
                    compute=compute, pipe=pipe)
                green_data.append(panorama)
            except HTTPError:
                new_broken_links[panorama.id] = True
            if pbar is not None:
                pbar.update()
        if len(new_broken_links) > 0:
            update_meta_links(self.broken_link_fp, new_broken_links)
        return green_data


def get_meta_links(link_fp):
    try:
        with open(link_fp, "r") as f:
            links = json.load(f)
    except FileNotFoundError:
        links = {}
    return links


def update_meta_links(link_fp, new_links):
    links = get_meta_links(link_fp)
    links.update(new_links)
    with open(link_fp, "w") as f:
        json.dump(links, f)
