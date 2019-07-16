
from models.deeplab import plot_segmentation

from os.path import splitext, join
from abc import ABC
import json
import numpy as np
from utils.size import b64_to_dict, dict_to_b64
from API.idgen import get_green_key


def _meta_fp(panorama_fp):
    base_fp = splitext(panorama_fp)[0]
    return base_fp+"_meta"+".json"


def _green_fractions(panorama_fp, seg_res, show=False):
    seg_map = np.array(seg_res['seg_map'])
    names = np.array(seg_res['color_map'][0])

    unique, counts = np.unique(seg_map, return_counts=True, axis=None)

    fractions = counts/seg_map.size
    if show:
        plot_segmentation(panorama_fp, seg_map, seg_res["color_map"])
    return dict(zip(names[unique], fractions))


class BasePanorama(ABC):
    " Object for using the Amsterdam data API"

    def __init__(self, meta_data, data_dir=None, data_src="unknown"):
        if data_dir is None:
            data_dir = data_src
        self.meta_data = meta_data
        self.data_dir = data_dir

        self.segments = {}
        self.greenery = {}
        self.temporary = False
        self.longitude = None
        self.latitude = None
        self.timestamp = None
        self.data_src = data_src

        self.fp_from_meta(meta_data)

        # Try to load the meta-data + results from file.
        try:
            self.load(self.meta_fp)
        except FileNotFoundError:
            self.parse(self.meta_data)
            self.save()
        self.segment_fp = join(data_dir, "segments.json")
        self.log_dict = self.todict()
        self.all_green_res = {}
        self.all_seg_res = {}

    def seg_analysis(self, seg_model, show=False, recalc=False):
        """
        Run a segmentation analysis on the panorama.

        Arguments
        ---------
        seg_model: SegmentationModel
            Instance of a segmentation model.
        show: bool
            Show the segmentation of the picture.
        recalc: bool
            Ignore the cached results.
        """
        model_id = seg_model.id()
        self.segment_fp = join(self.data_dir, "segment.json")
        self.load_segmentation(self.segment_fp)
        if model_id not in self.all_seg_res or show or recalc:
#             print(f"{model_id}, {show}, {recalc}, {self.panorama_fp}")
            self.all_seg_res[model_id] = self.seg_run(seg_model, show)
#             print(self.all_seg_res)
            self.save_segmentation(self.segment_fp)

    def green_analysis(self, seg_model, green_model):
        """
        Run a greenery analysis on the panorama and store it.

        Arguments
        ---------
        seg_model: SegmentationModel
            Instance of a segmentation model (DeepLabModel).
        green_model: GreenModel
            Instance of a greenery model (VegetationGreenery).

        Returns
        -------
        float:
            Greenery value.
        """
        green_id = green_model.id()

        # Run the segmentation model if not already done.
        seg_id = seg_model.id()

        green_fp = join(self.data_dir, "greenery.json")
        # Run greenery analysis if not already done.
        self.load_greenery(green_fp)
        key = get_green_key(self.__class__, seg_id, green_id)
        if key not in self.all_green_res:
            if seg_id not in self.all_seg_res:
                self.seg_analysis(seg_model)
            seg_res = self.all_seg_res[seg_id]
            seg_frac = _green_fractions(self.panorama_fp, seg_res)
#             print(seg_frac)
            self.all_green_res[key] = seg_frac
#             green_model.test(seg_frac)
            self.save_greenery(green_fp)
        return green_model.test(self.all_green_res[key])

    def load_greenery(self, green_fp):
        self.all_green_res = {}
        try:
            with open(green_fp, "r") as fp:
                self.all_green_res = json.load(fp)
        except FileNotFoundError:
            pass

    def save_greenery(self, green_fp):
        with open(green_fp, "w") as fp:
            json.dump(self.all_green_res, fp, indent=2)

    def save(self):
        """ Save the logs to a file. """
        log_dict = self.todict()
        with open(self.meta_fp, "w") as f:
            json.dump(log_dict, f, indent=2)

    def load(self, meta_fp):
        """ Load the logs from a file. """
        self.meta_fp = meta_fp
        with open(meta_fp, "r") as f:
            log_dict = json.load(f)
        self.fromdict(log_dict)

    def load_segmentation(self, segment_fp):
        self.all_seg_res = {}
        try:
            with open(segment_fp, "r") as f:
                zipped_seg_res = json.load(f)
                for name in zipped_seg_res:
                    zsr = zipped_seg_res[name]
                    usr = b64_to_dict(zsr)
                    self.all_seg_res[name] = usr
        except FileNotFoundError:
            pass

    def save_segmentation(self, segment_fp):
        zipped_seg_res = {}
        for name in self.all_seg_res:
            zsr = dict_to_b64(self.all_seg_res[name])
            zipped_seg_res[name] = zsr

#         print(zipped_seg_res)
        with open(segment_fp, "w") as f:
            json.dump(zipped_seg_res, f)

    def todict(self):
        " Put data in a dictionary. "
        log_dict = {
            "data_src": self.data_src,
            "panorama_fp": self.panorama_fp,
            "segments": self.segments,
            "greenery": self.greenery,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timestamp": self.timestamp,
            "meta_data": self.meta_data,
        }
        return log_dict

    def fromdict(self, log_dict):
        " Collect data from dictionary. "
        self.data_src = log_dict["data_src"]
        self.panorama_fp = log_dict["panorama_fp"]
        self.segments = log_dict["segments"]
        self.greenery = log_dict["greenery"]
        self.latitude = log_dict["latitude"]
        self.longitude = log_dict["longitude"]
        self.timestamp = log_dict["timestamp"]
        self.meta_data = log_dict["meta_data"]
