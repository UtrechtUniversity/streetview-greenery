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
    res_copy['seg_map'] = np.array(results['seg_map'])
    names = np.array(results['color_map'][0])
    colors = np.array(results['color_map'][0])
    res_copy['color_map'] = (names, colors)


def _meta_fp(panorama_fp):
    base_fp = splitext(panorama_fp)[0]
    return base_fp+"_meta"+".json"


class MetaLogger(object):
    " Object for storing results and meta-data. "

    def __init__(self, meta_fp=None, panorama_fp=None):
        """ Initialize the logger and load the data if available. """
        self.meta_fp = meta_fp
        self.panorama_fp = panorama_fp
        if meta_fp is None:
            if panorama_fp is None:
                self.panorama_fp = None
                self.log_dict = {'segmentation': {}}
            else:
                self.panorama_fp = self.panorama_fp
                self.meta_fp = _meta_fp(self.panorama_fp)
                try:
                    self.load(self.meta_fp)
                except FileNotFoundError:
                    self.log_dict = {'segmentation': {}}
        else:
            self.load(self.meta_fp)

#         self.save()

    def add_results(self, results, results_id="default"):
        """ Store segmentation results. """
        results = results_to_list(results)
        self.log_dict['segmentation'][results_id] = results
#         self.save()

    def add_greenery(self, greenery, model_id, green_id='greenery'):
        """ Store the greenery results. """

        if model_id not in self.log_dict['segmentation']:
            self.log_dict['segmentation'][model_id] = {}
        self.log_dict['segmentation'][model_id][green_id] = greenery
#         self.save()

    def save(self):
        """ Save the logs to a file. """
        with open(self.meta_fp, "w") as f:
            json.dump(self.log_dict, f, indent=2)

    def load(self, meta_fp):
        """ Load the logs from a file. """
        self.meta_fp = meta_fp
        with open(meta_fp, "r") as f:
            self.log_dict = json.load(f)
