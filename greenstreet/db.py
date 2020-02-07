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
            exist_id = db.execute('SELECT id FROM download WHERE pano_id is ? AND pano_type_id is ?',
                                  (pano_id, pano_type_id)).fetchone()
            if exist_id is not None:
                continue
            db.execute('INSERT INTO download (pano_id, pano_type_id, complete) VALUES'
                       '(?, ?, ?) ', (pano_id, pano_type_id, complete))
            db.commit()
#             print(picture_dict)
#             print(listdir(pic_dir))
