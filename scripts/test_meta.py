#!/usr/bin/env python

from greenstreet.meta import AdamMetaData

meta_data = AdamMetaData.from_download(
    param={"time_stamp_before": "2016-04-20",
           "time_stamp_after": "2016-04-01",
           "limit_results": 10,
           "page_size": 5})

print(meta_data.coordinates())
print(meta_data.timestamps())

meta_data.to_file("meta.json")

meta_data2 = AdamMetaData.from_file("meta.json")
print(meta_data2.timestamps())
meta_data2.to_file(meta_fp="meta2.json")

print(type(meta_data.meta_timestamp))
print(type(meta_data2.meta_timestamp))
