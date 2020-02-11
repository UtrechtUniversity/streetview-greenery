import os
from abc import ABC, abstractmethod
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
            return STATUS_FAIL

        try:
            seg_res = self._segmentation(data_dir)
        except FileNotFoundError:
            return STATUS_FAIL

        save_segmentation(seg_res, seg_fp)
        return STATUS_OK

    def greenery(self, data_dir):
        seg_fp = self.segmentation_file(data_dir)
        green_fp = self.greenery_file(data_dir)

        if isfile(green_fp):
            return STATUS_OK

        if self.green_model is None:
            return STATUS_FAIL

        try:
            seg_res = load_segmentation(seg_fp)
        except FileNotFoundError:
            return STATUS_FAIL

        self._greenery(seg_res, self.green_model)
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
                    self.seg_model.name + ".json")

    def execute(self, data_dir, *args, program="download", **kwargs):
        if program == "download":
            return self.download(data_dir, *args, **kwargs)
        if program == "segmentation":
            return self.segmentation(data_dir, *args, **kwargs)
        if program == "greenery":
            return self.greenery(data_dir, *args, **kwargs)
        return STATUS_FAIL


def save_segmentation(seg_res, segment_fp):
    zipped_seg_res = {}
    for seg_id in seg_res:
        zipped_seg_res[seg_id] = {}
        for name in seg_res[seg_id]:
            zsr = dict_to_b64(seg_res[seg_id][name])
            zipped_seg_res[seg_id][name] = zsr

    with open(segment_fp, "w") as f:
        json.dump(zipped_seg_res, f)


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
