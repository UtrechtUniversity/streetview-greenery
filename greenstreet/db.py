import os
from os import listdir
from os.path import dirname, isfile, join, isdir
import pkg_resources
import sqlite3
import json

import pandas as pd

from greenstreet.utils.time_conversion import get_time_from_str
from greenstreet.config import INV_PICTURE_NAMES, PICTURE_NAMES


def get_db(db_file):
    db_dir = dirname(db_file)
    if db_dir != '':
        os.makedirs(db_dir, exist_ok=True)
    db = sqlite3.connect(
        db_file, detect_types=sqlite3.PARSE_DECLTYPES)
    db.row_factory = sqlite3.Row
    return db


class GreenStreetDB():
    def __init__(self, db_file):
        self.db_file = db_file
        if not isfile(db_file):
            self.init_db()

    def init_db(self):
        db = get_db(self.db_file)
        schema_fp = pkg_resources.resource_filename(
            'greenstreet', 'schema.sql')
        with open(schema_fp, "r") as fp:
            script = fp.read()
            db.executescript(script)
        db.close()

    def __str__(self):
        table_names = [
            'panorama', 'download', 'segment', 'greenery', 'queries',
            'panorama_type', 'segment_type', 'green_type', 'tile',
            'green_class', 'result'
        ]
        db = get_db(self.db_file)
        db_string = ""
        for table in table_names:
            db_string += "\n+++++++++++++++++++++++++\n"
            db_string += f"Table:  {table}\n"
            db_string += str(pd.read_sql_query(f"SELECT * FROM {table}", db))
            db_string += "\n-------------------------\n"
        return db_string

    def insert_from_dir(self, data_dir):
        base_tile_dir = join(data_dir, "tiles")
        all_dirs = [d for d in listdir(base_tile_dir)]
        tiles = [d for d in all_dirs if d != "cache" and
                 isdir(join(base_tile_dir, d))]

        db = get_db(self.db_file)
        self.insert_tiles(tiles)
        for tile in tiles:
            tile_dir = join(base_tile_dir, tile)
            base_pic_dir = join(tile_dir, "pics")
            pic_dirs = [join(base_pic_dir, d) for d in listdir(base_pic_dir)
                        if isfile(join(base_pic_dir, d, "meta.json"))]

            tile_id = db.execute("SELECT id FROM tile WHERE name is ?",
                                 (tile, )).fetchone()['id']
            self.insert_pictures(pic_dirs, tile_id, db)
            self.update_queries(join(tile_dir, "queries"), tile_id, db)

    def insert_tiles(self, tiles):
        db = get_db(self.db_file)
        for tile in tiles:
            try:
                db.execute(
                    f"INSERT INTO tile (name) VALUES (?)",
                    (tile, ))
                db.commit()
            except sqlite3.IntegrityError:
                pass

    def insert_pictures(self, pic_dirs, tile_id, db):
        green_class_ids = get_green_class_ids(db)
        for pic_dir in pic_dirs:
            meta_file = join(pic_dir, "meta.json")
            with open(meta_file, "r") as fp:
                meta_data = json.load(fp)
            pano_name = meta_data["pano_id"]
            latitude = meta_data["latitude"]
            longitude = meta_data["longitude"]
            timestamp = meta_data["timestamp"]
            try:
                db.execute(
                    'INSERT INTO panorama (name, tile_id, latitude, longitude,'
                    ' created) VALUES (?, ?, ?, ?, ?)',
                    (pano_name, tile_id, latitude, longitude,
                     get_time_from_str(timestamp))
                    )
                db.commit()
            except sqlite3.IntegrityError:
                pass
            pano_id = db.execute('SELECT id FROM panorama WHERE name is ?',
                                 (pano_name, )).fetchone()["id"]
            self.update_download(join(pic_dir, "pictures"),
                                 pano_id, db)
            self.update_segmentation(join(pic_dir, "segmentations"),
                                     pano_id, db)
            self.update_greenery(join(pic_dir, "greenery"), pano_id, db,
                                 green_class_ids)

    def update_download(self, pic_dir, pano_id, db):
        if not os.path.isdir(pic_dir):
            return
        picture_files = [f for f in listdir(pic_dir)
                         if f in INV_PICTURE_NAMES]
        picture_dict = {}
        for picture in picture_files:
            pic_type = INV_PICTURE_NAMES[picture]
            if pic_type not in picture_dict:
                picture_dict[pic_type] = []
            picture_dict[pic_type].append(picture)
        for pic_type, file_names in picture_dict.items():
            complete = 0
            if len(file_names) == len(PICTURE_NAMES[pic_type]):
                complete = 1
            try:
                db.execute('INSERT INTO panorama_type (name) VALUES (?)',
                           (pic_type,))
                db.commit()
            except sqlite3.IntegrityError:
                pass
            pano_type_id = db.execute('SELECT id FROM panorama_type WHERE name is ?',
                                      (pic_type,)).fetchone()['id']
            exist_id = db.execute('SELECT id FROM download WHERE pano_id is ? '
                                  'AND pano_type_id is ?',
                                  (pano_id, pano_type_id)).fetchone()
            if exist_id is not None:
                continue
            db.execute('INSERT INTO download (pano_id, pano_type_id, complete) VALUES'
                       '(?, ?, ?) ', (pano_id, pano_type_id, complete))
            db.commit()

    def update_segmentation(self, seg_dir, pano_id, db):
        if not os.path.isdir(seg_dir):
            return

        seg_files = [join(seg_dir, f) for f in listdir(seg_dir)]
        for seg_file in seg_files:
            with open(seg_file, "r") as fp:
                seg_res = json.load(fp)
            panorama_type = seg_res["panorama_type"]
            seg_type = seg_res["segmentation_model"]

            pano_type_id = get_pano_type_id(panorama_type, db)
            seg_type_id = get_seg_type_id(seg_type, db)
            exist_id = db.execute('SELECT id FROM segment WHERE pano_id is ? '
                                  'AND pano_type_id is ? AND seg_type_id is ?',
                                  (pano_id, pano_type_id, seg_type_id)
                                  ).fetchone()
            if exist_id is not None:
                continue
            db.execute('INSERT INTO segment (pano_id, pano_type_id, seg_type_id)'
                       ' VALUES (?, ?, ?) ', (pano_id, pano_type_id, seg_type_id))
            db.commit()

    def update_greenery(self, green_dir, pano_id, db, green_class_ids):
        if not os.path.isdir(green_dir):
            return

        green_files = [join(green_dir, f) for f in listdir(green_dir)]
        for green_file in green_files:
            with open(green_file, "r") as fp:
                green_res = json.load(fp)
            pano_type_id = get_pano_type_id(green_res["panorama_type"], db)
            seg_type_id = get_seg_type_id(green_res["segmentation_model"], db)
            green_type_id = get_green_type_id(green_res["greenery_model"], db)
            exist_id = db.execute('SELECT id FROM greenery WHERE pano_id is ? '
                                  'AND pano_type_id is ? AND seg_type_id is ? '
                                  'AND green_type_id is ?',
                                  (pano_id, pano_type_id, seg_type_id,
                                   green_type_id)
                                  ).fetchone()
            if exist_id is not None:
                continue
            db.execute('INSERT INTO greenery (pano_id, pano_type_id, '
                       'seg_type_id, green_type_id) VALUES (?, ?, ?, ?)',
                       (pano_id, pano_type_id, seg_type_id, green_type_id))
            db.commit()

            green_id = db.execute(
                'SELECT id FROM greenery WHERE pano_id is ? AND pano_type_id is ?'
                ' AND seg_type_id is ? AND green_type_id is ?',
                (pano_id, pano_type_id, seg_type_id, green_type_id)).fetchone()["id"]
            green_fracs = green_res["greenery_fractions"]
            for green_class, green_frac in green_fracs.items():
                if green_class not in green_class_ids:
                    green_class_ids[green_class] = insert_green_class(green_class, db)
                exist_id = db.execute(
                    'SELECT id FROM result WHERE green_id is ? AND '
                    'green_class_id is ?', (green_id, green_class_ids[green_class])
                    ).fetchone()
                if exist_id is None:
                    db.execute(
                        'INSERT INTO result (value, green_class_id, green_id) '
                        'VALUES (?, ?, ?)',
                        (green_frac, green_class_ids[green_class], green_id)
                    )
                    db.commit()

    def update_queries(self, query_dir, tile_id, db):
        if not os.path.isdir(query_dir):
            return
        query_files = [join(query_dir, f) for f in listdir(query_dir)]
        for query_file in query_files:
            with open(query_file, "r") as fp:
                query_data = json.load(fp)
            grid_level = query_data["grid_level"]
            pano_ids = query_data["pano_ids"]
            for pano_name in pano_ids:
                pano_id = db.execute(
                    'SELECT id FROM panorama WHERE name is ?',
                    (pano_name, )).fetchone()
                if pano_id is None:
                    continue
                pano_id = pano_id["id"]
                exist_id = db.execute(
                    'SELECT id FROM queries WHERE grid_level is ? AND '
                    'tile_id is ? AND pano_id is ?',
                    (grid_level, tile_id, pano_id)).fetchone()
                if exist_id is None:
                    db.execute('INSERT INTO queries (grid_level, tile_id, '
                               'pano_id) VALUES (?, ?, ?)',
                               (grid_level, tile_id, pano_id))
                    db.commit()


def get_pano_type_id(pano_type, db):
    pano_type_id = db.execute('SELECT id FROM panorama_type WHERE name is ?',
                              (pano_type,)).fetchone()
    if pano_type_id is None:
        db.execute('INSERT INTO panorama_type (name) VALUES (?)',
                   (pano_type,))
        db.commit()
        return db.execute('SELECT id FROM panorama_type WHERE name is ?',
                          (pano_type,)).fetchone()["id"]
    return pano_type_id["id"]


def get_seg_type_id(seg_type, db):
    seg_type_id = db.execute('SELECT id FROM segment_type WHERE name is ?',
                             (seg_type,)).fetchone()
    if seg_type_id is None:
        db.execute('INSERT INTO segment_type (name) VALUES (?)',
                   (seg_type,))
        db.commit()
        return db.execute('SELECT id FROM segment_type WHERE name is ?',
                          (seg_type,)).fetchone()["id"]
    return seg_type_id["id"]


def get_green_type_id(green_type, db):
    green_type_id = db.execute('SELECT id FROM green_type WHERE name is ?',
                               (green_type,)).fetchone()
    if green_type_id is None:
        db.execute('INSERT INTO green_type (name) VALUES (?)',
                   (green_type,))
        db.commit()
        return db.execute('SELECT id FROM green_type WHERE name is ?',
                          (green_type,)).fetchone()["id"]
    return green_type_id["id"]


def insert_green_class(green_class, db):
    db.execute('INSERT INTO green_class (name) VALUES (?)',
               (green_class,))
    db.commit()
    return db.execute('SELECT id FROM green_class WHERE name is ?',
                      (green_class,)).fetchone()["id"]


def get_green_class_ids(db):
    green_class_ids = db.execute(
        'SELECT name, id FROM green_class').fetchall()
    if green_class_ids is None:
        return {}
    return {row["name"]: row["id"] for row in green_class_ids}
