#!/bin/bash

cd data.amsterdam/tiles
rsync -zarv --include="greenery.json" --include="meta_srid*.json" --include="*/" --exclude="*" lisa:~/streetview/streetview-greenery/data.amsterdam/tiles/ .

scp lisa:~/streetview/streetview-greenery/data.amsterdam/tiles/empty_tiles_1024m.json .
