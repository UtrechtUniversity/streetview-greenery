import json
from pathlib import Path
from greenstreet.API.adam.meta import AdamMetaData
from json.decoder import JSONDecodeError
from greenstreet.config import STATUS_FAIL


DOWNLOAD_SUCCESS = 0
DOWNLOAD_FAIL = 1


class Tile():
    def __init__(self, tile_name, bbox, tile_dir, meta_class=AdamMetaData):
        self.tile_name = tile_name
        self.tile_dir = tile_dir
        self.bbox = bbox
        self.tile_fp = Path(tile_dir, "tile.json")
        self.result_fp = Path(tile_dir, "results.json")
        self.query_dir = Path(tile_dir, "queries")
        self.meta_fp = Path(tile_dir, "meta.json")
        self.meta_class = meta_class
        self._tile_data = None
        self._meta_data = None
        self._result_data = None

    def get_results(self, job_runner, query):
        result_data = self.result_data
        result_id = _result_id(job_runner, query)
        if result_id in result_data:
            return result_data[result_id]
        return None

    def get_pano_ids(self, query):
        pano_id_fp = _pano_id_fp(query, self.query_dir)
        if pano_id_fp.exists():
            with open(pano_id_fp, "r") as f:
                try:
                    pano_ids = json.load(f)
                    return pano_ids
                except JSONDecodeError:
                    pass

        pano_ids = query.sample_panoramas(self.meta_data).tolist()
        pano_id_fp.parent.mkdir(exist_ok=True, parents=True)
        with open(pano_id_fp, "w") as f:
            json.dump(pano_ids, f)
        return pano_ids

    def get_jobs(self, job_runner, query, job_type="greenery"):
        result_data = self.result_data
        result_id = "_".join([job_runner.name, query.name])
        if result_id in result_data:
            return {}

        pano_ids = self.get_pano_ids(query)
        td = self.tile_data
        jobs = {}
        for pano_id in pano_ids:
            data_dir = _data_dir(self.tile_dir, pano_id)
            add_jobs(pano_id, td, job_runner, job_type, jobs, data_dir)

        return jobs

    def prepare(self, jobs):
        pano_ids = []
        for pano_id, pipe in jobs.items():
            if pipe[0]["program"] == "download":
                pano_ids.append(pano_id)

        meta_data = self.meta_data
        for pano_id in pano_ids:
            pano_dir = _data_dir(self.tile_dir, pano_id)
            pano_dir.mkdir(exist_ok=True, parents=True)
            meta_data.to_file(Path(pano_dir, "meta.json"), pano_id=pano_id)

    def submit_result(self, jobs, results, job_runner, query=None):
        tile_data = self.tile_data
        result_data = self.result_data
        new_result_data = {}
        for pano_id, pipe in jobs.items():
            for i_job, job in enumerate(pipe):
                program = job["program"]
                if program == "download":
                    res_id = job_runner.pic_type
                elif program == "segmentation":
                    res_id = job_runner.seg_id
                else:
                    res_id = job_runner.name
                if res_id not in tile_data[program]:
                    tile_data[program][res_id] = {}
                tile_data[program][res_id][pano_id] = results[
                    pano_id][i_job]
                if (job["program"] == "greenery" and query is not None
                        and results[pano_id][i_job]["status"] != STATUS_FAIL):
                    new_result_data[pano_id] = {
                        "fractions": results[pano_id][i_job]["data"],
                        "meta": tile_data["download"][job_runner.pic_type][pano_id]["data"],
                    }

        if query is not None:
            query_id = "_".join([job_runner.name, query.name])
            pano_ids = [pano_id for pano_id in new_result_data]
            timestamp = [new_result_data[pano_id]["meta"]["timestamp"]
                         for pano_id in pano_ids]
            latitude = [new_result_data[pano_id]["meta"]["latitude"]
                        for pano_id in pano_ids]
            longitude = [new_result_data[pano_id]["meta"]["longitude"]
                         for pano_id in pano_ids]
            data = {green_class: [] for green_class in new_result_data[
                pano_ids[0]]["fractions"]}
            for pano_id in pano_ids:
                for green_class in data:
                    data[green_class].append(
                        new_result_data[pano_id]["fractions"][green_class])
            result_data[query_id] = {
                "timestamp": timestamp,
                "latitude": latitude,
                "longitude": longitude,
                "data": data,
            }

    def save(self):
        if self._result_data is not None:
            with open(self.result_fp, "w") as f:
                json.dump(self._result_data, f)
        if self._tile_data is not None:
            with open(self.tile_fp, "w") as f:
                json.dump(self._tile_data, f)

    @property
    def param(self):
        bb_string = str(self.bbox[0][1]) + "," + str(self.bbox[1][0]) + "," + \
            str(self.bbox[1][1]) + "," + str(self.bbox[0][0])
        return {"bbox": bb_string}

    @property
    def tile_data(self):
        if self._tile_data is None:
            if self.tile_fp.exists():
                with open(self.tile_fp, "r") as f:
                    self._tile_data = json.load(f)
            else:
                self._tile_data = _new_tile_data()
        return self._tile_data

    @property
    def meta_data(self):
        if self._meta_data is None:
            try:
                self._meta_data = self.meta_class.from_file(self.meta_fp)
            except FileNotFoundError:
                self._meta_data = self.meta_class.from_download(self.param)
                Path(self.tile_dir).mkdir(parents=True, exist_ok=True)
                self._meta_data.to_file(self.meta_fp)
        return self._meta_data

    @property
    def result_data(self):
        if self._result_data is None:
            if self.result_fp.exists():
                with open(self.result_fp, "r") as f:
                    self._result_data = json.load(f)
            else:
                self._result_data = _new_result_data()
        return self._result_data

    def load(self):
        pass


def add_jobs(pano_id, tile_data, job_runner, job_type, jobs, data_dir):
    new_jobs = []
    if job_type == "greenery":
        green_id = job_runner.name
        try:
            green_res = tile_data["greenery"][green_id][pano_id]
            return
        except KeyError:
            new_jobs.append({
                "data_dir": data_dir,
                "program": "greenery",
            })

    if job_type in ["segmentation", "greenery"]:
        seg_id = "_".join([job_runner.pic_type, job_runner.seg_model.name])
        try:
            seg_res = tile_data["segmentation"][seg_id][pano_id]
            if len(new_jobs):
                jobs[pano_id] = new_jobs
            return
        except KeyError:
            new_jobs.append({
                "data_dir": data_dir,
                "program": "segmentation",
            })

    try:
        down_res = tile_data["download"][job_runner.pic_type][pano_id]
        if down_res["status"] == DOWNLOAD_FAIL:
            return
        if len(new_jobs):
            new_jobs.reverse()
            jobs[pano_id] = new_jobs
        return
    except KeyError:
        new_jobs.append({
            "data_dir": data_dir,
            "program": "download",
        })
    if len(new_jobs):
        new_jobs.reverse()
        jobs[pano_id] = new_jobs


def _data_dir(tile_dir, pano_id):
    return Path(tile_dir, "pics", pano_id)


def _new_tile_data():
    return {
        "download": {},
        "segmentation": {},
        "greenery": {},
    }


def _new_result_data():
    return {
    }


def _result_fp(job_runner, query, result_dir):
    result_id = "_".join([job_runner.name, query.name])
    result_fp = Path(result_dir, f"{result_id}.json")
    return result_fp


def _pano_id_fp(query, result_dir):
    return Path(result_dir, f"{query.name}.json")


def _result_id(job_runner, query):
    return "_".join([job_runner.name, query.name])
