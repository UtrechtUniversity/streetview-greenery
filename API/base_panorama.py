from os.path import splitext
from abc import ABC
import json


def _meta_fp(panorama_fp):
    base_fp = splitext(panorama_fp)[0]
    return base_fp+"_meta"+".json"


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
        self.data_src = data_src

        self.fp_from_meta(meta_data)

        # Try to load the meta-data + results from file.
        try:
            self.load(self.meta_fp)
        except FileNotFoundError:
            self.parse(self.meta_data)
            self.save()
        self.log_dict = self.todict()

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
        if model_id not in self.segments or show or recalc:
            print(f"{model_id}, {show}, {recalc}, {self.panorama_fp}")
            self.segments[model_id] = self.seg_run(seg_model, show)
            self.save()

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
        if seg_id not in self.segments:
            self.seg_analysis(seg_model)
        seg_res = self.segments[seg_id]

        # Run greenery analysis if not already done.
        if seg_id not in self.greenery:
            self.greenery[seg_id] = {}
        green_dict = self.greenery[seg_id]
        if green_id not in self.greenery[seg_id]:
            green_dict[green_id] = green_model.test(seg_res)
            self.save()
        return self.greenery[seg_id][green_id]

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

    def todict(self):
        " Put data in a dictionary. "
        log_dict = {
            "data_src": self.data_src,
            "panorama_fp": self.panorama_fp,
            "segments": self.segments,
            "greenery": self.greenery,
            "latitude": self.latitude,
            "longitude": self.longitude,
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
        self.meta_data = log_dict["meta_data"]
        