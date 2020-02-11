#!/usr/bin/env python

from greenstreet import GreenStreetDB

db = GreenStreetDB("test.db")

# print(db)
db.insert_from_dir("output/oosterpark")
print(db)
