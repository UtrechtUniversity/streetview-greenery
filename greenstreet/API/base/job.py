import os
from abc import ABC
from os.path import join, isfile
import json
from json.decoder import JSONDecodeError

from greenstreet.config import STATUS_OK, STATUS_FAIL
from greenstreet.utils.size import b64_to_dict, dict_to_b64


class GreenJob(ABC):
    name = "base"

    def __init__(self, seg_model=None, green_model=None):
        self.seg_model = seg_model
        self.green_model = green_model

    def download(self, data_dir, n_try=5, timeout=3):
        meta_fp = os.path.join(data_dir, "meta.json")
        picture_dir = os.path.join(data_dir, "pictures")
        os.makedirs(picture_dir, exist_ok=True)
        try:
            with open(meta_fp, "r") as fp:
                meta_data = json.load(fp)
        except FileNotFoundError:
            return STATUS_FAIL, f"File '{meta_fp}' not found."
        except JSONDecodeError:
            return STATUS_FAIL, f"File '{meta_fp}' unreadable (JSON Error)"
        return self._download(meta_data, picture_dir, n_try=n_try,
                              timeout=timeout)

    def segmentation(self, data_dir):
        seg_fp = self.segmentation_file(data_dir)

        if isfile(seg_fp):
            return STATUS_OK

        if self.seg_model is None:
            return STATUS_FAIL, "No valid segmentation model supplied."

        try:
            seg_res = self._segmentation(self.seg_model, data_dir)
        except FileNotFoundError:
            return STATUS_FAIL, "Panorama(s) not found."

        save_segmentation(seg_res, seg_fp, panorama_type=self.name,
                          segmentation_model=self.seg_model.name)
        return STATUS_OK

    def greenery(self, data_dir):
        seg_fp = self.segmentation_file(data_dir)
        green_fp = self.greenery_file(data_dir)

        if isfile(green_fp):
            return STATUS_OK

        if self.green_model is None:
            return STATUS_FAIL

        try:
            seg_res, pano_type, seg_model = load_segmentation(seg_fp)
            if pano_type != self.name:
                return STATUS_FAIL, "Panorama type that was loaded is wrong."
            if seg_model != self.seg_model.name:
                return STATUS_FAIL, "Wrong segmentation type that was loaded."
        except FileNotFoundError:
            return STATUS_FAIL, f"Segmentation file {seg_fp} does not exist."

        green_res = self._greenery(seg_res, self.green_model)
        with open(green_fp, "w") as fp:
            json.dump({
                "greenery_fractions": green_res,
                "segmentation_model": self.seg_model.name,
                "greenery_model": self.green_model.name,
                "panorama_type": self.name
            }, fp, indent=4)
        return STATUS_OK

    def segmentation_file(self, data_dir):
        seg_dir = join(data_dir, "segmentations")
        os.makedirs(seg_dir, exist_ok=True)
        return join(data_dir, "segmentations", self.name + "_" +
                    self.seg_model.name + ".json")

    def greenery_file(self, data_dir):
        green_dir = join(data_dir, "greenery")
        os.makedirs(green_dir, exist_ok=True)
        return join(green_dir, self.name + "_" +
                    self.seg_model.name + "_" + self.green_model.name
                    + ".json")

    def execute(self, data_dir, *args, program="download", **kwargs):
        if program == "download":
            return self.download(data_dir, *args, **kwargs)
        if program == "segmentation":
            return self.segmentation(data_dir, *args, **kwargs)
        if program == "greenery":
            return self.greenery(data_dir, *args, **kwargs)
        return STATUS_FAIL, f"program '{program}' unknown."


def save_segmentation(seg_res, segment_fp, panorama_type, segmentation_model):
    zipped_seg_res = {"seg_res": {}}
    for image_name, image_seg in seg_res.items():
        zipped_seg_res["seg_res"][image_name] = dict_to_b64(image_seg)

    zipped_seg_res["panorama_type"] = panorama_type
    zipped_seg_res["segmentation_model"] = segmentation_model
    with open(segment_fp, "w") as f:
        json.dump(zipped_seg_res, f)


def unzip_segmentation(zipped_segmentation):
    segmentation = {}
    for image_name, zsr in zipped_segmentation.items():
        segmentation[image_name] = b64_to_dict(zsr)
    return segmentation


def load_segmentation(segment_fp):
    seg_res = {}
    with open(segment_fp, "r") as f:
        segmentation = json.load(f)
    seg_res = unzip_segmentation(segmentation["seg_res"])
    panorama_type = segmentation["panorama_type"]
    segmentation_model = segmentation["segmentation_model"]
    return seg_res, panorama_type, segmentation_model
