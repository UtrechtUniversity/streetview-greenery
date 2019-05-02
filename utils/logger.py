" Class for logging meta data and results. "
from os.path import splitext
import json
import numpy as np


def results_to_list(results):
    res_copy = {}
    if 'seg_map' in results:
        res_copy['seg_map'] = results['seg_map'].tolist()
        color_map = results['color_map']
        names = color_map[0].tolist()
        colors = color_map[1].tolist()

        res_copy['color_map'] = (names, colors)
        return res_copy
    else:
        return results


def results_to_numpy(results):
    res_copy = {}
    if 'seg_map' not in results:
        return results
    res_copy['seg_map'] = np.ndarray(results['seg_map'])
    names = np.ndarray(results['color_map'][0])
    colors = np.ndarray(results['color_map'][0])
    res_copy['color_map'] = (names, colors)


def _meta_fp(panorama_fp):
    base_fp = splitext(panorama_fp)[0]
    return base_fp+"_meta"+".json"


class MetaLogger(object):
    " Object for storing results and meta-data. "

    def __init__(self, meta_fp=None, panorama_fp=None):
        self.meta_fp = meta_fp
        self.panorama_fp = panorama_fp
        if meta_fp is None:
            if panorama_fp is None:
                self.panorama_fp = None
                self.log_dict = {'results': {}}
            else:
                self.panorama_fp = self.panorama_fp
                self.meta_fp = _meta_fp(self.panorama_fp)
                try:
                    self.load(self.meta_fp)
                except FileNotFoundError:
                    self.log_dict = {'results': {}}
        else:
            self.load(self.meta_fp)

    def add_meta_data(self, meta_data={}, panorama_fp=None):
        self.log_dict["meta_data"] = meta_data
        if panorama_fp is not None:
            self.panorama_fp = panorama_fp
        if self.panorama_fp is None:
            raise ValueError("Need panorama file name to store meta data.")
        self.meta_fp = _meta_fp(self.panorama_fp)
        self.log_dict['panorama_fp'] = self.panorama_fp
        self.log_dict['meta'] = meta_data
        self.save()

    def add_results(self, results, results_id="default"):
        results = results_to_list(results)
        self.log_dict['results'][results_id] = results
#         print(self.log_dict)
        self.save()

    def save(self):
        with open(self.meta_fp, "w") as f:
            json.dump(self.log_dict, f, indent=2)

    def load(self, meta_fp):
        self.meta_fp = meta_fp
        with open(meta_fp, "r") as f:
            self.log_dict = json.load(f)
