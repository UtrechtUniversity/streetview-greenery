#!/usr/bin/env python

import os

from greenstreet import GreenStreetDB


output_dir = os.path.join("output", "oosterpark")
db_fp = os.path.join(output_dir, "results.db")
db = GreenStreetDB(db_fp)
db.insert_from_dir(output_dir)

print(db)
