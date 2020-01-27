#!/bin/bash

cd data.amsterdam/tiles
rsync -zarv --include="*lvl*.json" --include="meta_srid*.json" --include="*/" --exclude="*" lisa:~/streetview/streetview-greenery/data.amsterdam/tiles/ .
scp lisa:~/streetview/streetview-greenery/data.amsterdam/tiles/empty_tiles_1024m.json .

mkdir -p ../krige
cd ../krige
rsync -zarv lisa:~/streetview/streetview-greenery/data.amsterdam/krige/ .

