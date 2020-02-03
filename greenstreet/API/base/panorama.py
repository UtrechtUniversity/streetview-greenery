from os.path import splitext, join, isfile
from abc import ABC, abstractmethod
import json
from json.decoder import JSONDecodeError
import os

from greenstreet.API.idgen import get_green_key
from greenstreet.utils.size import b64_to_dict, dict_to_b64


def _meta_fp(panorama_fp):
    base_fp = splitext(panorama_fp)[0]
    return base_fp+"_meta"+".json"


# def _green_fractions(seg_res):
#     seg_map = np.array(seg_res['seg_map'])
#     names = np.array(seg_res['color_map'][0])
# 
#     unique, counts = np.unique(seg_map, return_counts=True, axis=None)
# 
#     fractions = counts/seg_map.size
#     return dict(zip(names[unique], fractions))


class BasePanorama(ABC):
    " Object for using the Amsterdam data API"
    name = "base"

    def __init__(self, meta_data):
        self.parse_meta_data(meta_data)

        self.is_downloaded = False
        self.seg_res = None
        self.green_res = None

        if not isfile(self.meta_fp):
            self.save_meta(self.meta_fp)

        self.green_fp = join(self.data_dir, "greenery.json")
        self.segment_fp = join(self.data_dir, "segment.json")
        self.log_dict = self.todict()
        self.all_green_res = {}
        self.all_seg_res = {}

    @abstractmethod
    def download(self, n_try=5, timeout=3):
        raise NotImplementedError

    @abstractmethod
    def compute_segmentation(self, model):
        raise NotImplementedError

    @abstractmethod
    def parse_meta_data(self, meta_data):
        raise NotImplementedError

    @abstractmethod
    def seg_to_green(self, seg_res, green_model=None):
        raise NotImplementedError

    def get_segmentation(self, seg_model, compute=False, pipe=True):
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
        if self.seg_res is not None:
            return self.seg_res

        seg_id = seg_model.id()
        self.all_seg_res = self.load_segmentation(self.segment_fp)
        try:
            self.seg_res = self.all_seg_res[seg_id][self.name]
        except KeyError:
            pass

        if self.seg_res is not None or not compute:
            return self.seg_res

        if not self.is_downloaded:
            if not pipe:
                return None
            self.download()

        self.seg_res = self.compute_segmentation(seg_model)
        self.all_seg_res[seg_id][self.name] = self.seg_res
        save_segmentation(self.all_seg_res, self.segment_fp)
        return self.all_seg_res[seg_id][self.name]

    def get_greenery(self, green_model, seg_model, compute=False, pipe=True):
        if self.green_res is not None:
            return self.green_res

        green_id = green_model.id()
        seg_id = seg_model.id()

        # Run the segmentation model if not already done.
        green_fp = join(self.data_dir, "greenery.json")
        green_key = get_green_key(self.name, seg_id, green_id)

        self.all_green_res = self.load_greenery(green_fp)
        if self.green_res is not None or not compute:
            return self.green_res

        if self.seg_res is None:
            if not pipe:
                return None
            self.get_segmentation(seg_model, compute=compute, pipe=True)

        self.green_res = self.seg_to_green(self.seg_res, green_model)
        self.all_green_res[green_key] = self.green_res
        self.save_greenery(green_fp)
        return green_res, self.latitude, self.longitude, self.timestamp

#     def compute_pipe(self, download=False, run_segmentation=False,
#                      run_greenery=False):
        
#     def seg_pipe(self, seg_model, show=False, recalc=False):
#         seg_id = seg_model.id()
#         self.load_segmentation(self.segment_fp)
# 
#         if seg_id in self.all_seg_res and not show or recalc:
#             found_seg = True
#             for name in self.seg_names:
#                 if name not in self.all_seg_res[seg_id]:
#                     found_seg = False
#                     break
#             if found_seg:
#                 return
# 
#         if not self.is_downloaded:
#             self.download()
#         self.all_seg_res[seg_id] = {}
#         self.all_seg_res[seg_id].update(self.seg_run(seg_model, show))
#         self.save_segmentation(self.segment_fp)

#     def green_analysis(self, seg_model, green_model):
#         """
#         Run a greenery analysis on the panorama and store it.
# 
#         Arguments
#         ---------
#         seg_model: SegmentationModel
#             Instance of a segmentation model (DeepLabModel).
#         green_model: GreenModel
#             Instance of a greenery model (VegetationGreenery).
# 
#         Returns
#         -------
#         float:
#             Greenery value.
#         """
#         green_id = green_model.id()
# 
#         # Run the segmentation model if not already done.
#         seg_id = seg_model.id()
# 
#         green_fp = join(self.data_dir, "greenery.json")
#         # Run greenery analysis if not already done.
#         self.load_greenery(green_fp)
#         key = get_green_key(self.__class__, seg_id, green_id)
#         if key not in self.all_green_res:
#             if seg_id not in self.all_seg_res:
#                 self.seg_analysis(seg_model)
#             seg_res = self.all_seg_res[seg_id]
#             seg_frac = _green_fractions(self.panorama_fp, seg_res)
#             self.all_green_res[key] = seg_frac
#             self.save_greenery(green_fp)
#         return green_model.test(self.all_green_res[key])
# 
#     def green_pipe(self, seg_model, green_model):
#         green_id = green_model.id()
# 
#         # Run the segmentation model if not already done.
#         seg_id = seg_model.id()
# 
#         green_fp = join(self.data_dir, "greenery.json")
#         green_key = get_green_key(self.name, seg_id, green_id)
# 
#         self.load_greenery(green_fp)
#         if green_key not in self.all_green_res:
#             if seg_id not in self.all_seg_res:
#                 self.seg_pipe(seg_model)
#             green_res = self.seg_to_green(self.all_seg_res[seg_id],
#                                           green_model)
#             self.all_green_res[green_key] = green_res
#             self.save_greenery(green_fp)
#         return green_model.test(self.all_green_res[green_key])

    def save_meta(self, meta_fp):
        """ Save the logs to a file. """
        log_dict = self.todict()
        os.makedirs(os.path.dirname(meta_fp), exist_ok=True)
        with open(meta_fp, "w") as f:
            json.dump(log_dict, f, indent=2)

    def load_meta(self, meta_fp):
        """ Load the logs from a file. """
        self.meta_fp = meta_fp
        with open(meta_fp, "r") as f:
            log_dict = json.load(f)
        self.fromdict(log_dict)

    def todict(self):
        " Put data in a dictionary. "
        log_dict = {
            "name": self.name,
            "panorama_fp": self.panorama_fp,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timestamp": self.timestamp,
            "meta_data": self.meta_data,
            "pano_id": self.id,
        }
        return log_dict

    def fromdict(self, log_dict):
        " Collect data from dictionary. "
        self.name = log_dict["name"]
        self.panorama_fp = log_dict["panorama_fp"]
        self.latitude = log_dict["latitude"]
        self.longitude = log_dict["longitude"]
        self.timestamp = log_dict["timestamp"]
        self.meta_data = log_dict["meta_data"]
        self.id = log_dict["pano_id"]


def unzip_segmentation(zipped_segmentation):
    segmentation = {}
    for seg_id in zipped_segmentation:
        segmentation[seg_id] = {}
        for name in zipped_segmentation[seg_id]:
            zsr = zipped_segmentation[seg_id][name]
            usr = b64_to_dict(zsr)
            segmentation[seg_id][name] = usr
    return segmentation


def load_segmentation(segment_fp):
    seg_res = {}
    try:
        with open(segment_fp, "r") as f:
            zipped_segmentation = json.load(f)
            seg_res = unzip_segmentation(zipped_segmentation)
    except FileNotFoundError:
        pass
    return seg_res


def save_segmentation(seg_res, segment_fp):
    zipped_seg_res = {}
    for seg_id in seg_res:
        zipped_seg_res[seg_id] = {}
        for name in seg_res[seg_id]:
            zsr = dict_to_b64(seg_res[seg_id][name])
            zipped_seg_res[seg_id][name] = zsr

    with open(segment_fp, "w") as f:
        json.dump(zipped_seg_res, f)


def load_greenery(green_fp):
    green_res = {}
    try:
        with open(green_fp, "r") as fp:
            green_res = json.load(fp)
    except (FileNotFoundError, JSONDecodeError):
        pass
    return green_res


def save_greenery(green_res, green_fp):
    with open(green_fp, "w") as fp:
        json.dump(green_res, fp, indent=2)
