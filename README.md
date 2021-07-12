# streetview-greenery

## Most of the package does not work anymore, because the municipality of amsterdam made their panorama data private.

Project to retrieve and process panoramic photo's and compute the greenery as perceived from street level.

## Description

The base idea of this package is to download street view panorama (or other) pictures and compute measures of greenness. The first step is to do a segmentation analysis: assigning object classes to individual pixels. The second step is to convert these segmented pictures into a measure of greenness. The last step is to create a map from individiual greenness measures.

## Example maps

Sampled map of Amsterdam/Almere: [link](https://qubixes.github.io/streetview-greenery/docs/adam_alm.html)

## Installation

There is at the moment no real installation script. First install the (non-python) GDAL library seperately. Then install the python bindings that has the same version (`pip install "gdal==x"`), where x is the version of your GDAL library. Finally install the remaining requirements using `pip install -r requirements.txt`.

## Quickstart [Command Line Interface]

There are two ways to interact with this package: Command Line Interfaces (CLI) or directly using it as a python library (API). The quickest way to start using the package is to use the CLI. There are several runnable files, the main one being "streetgreen.py".



#### Creating a dataset [street_green.py]

The script "streetgreen.py" is the workhorse of the package, downloading and processing images, doing spatial kriging and creating maps. Currently a single data source is included, which is panoramas provided freely by the municipality of Amsterdam: [data.amsterdam.nl](https://data.amsterdam.nl).

By default the program will select some area in Amsterdam/Almere and it will sample panoramas in a grid. At the coarsest level it will obtain one data point for each 1km x 1km tile. Then from the greenery measure of each of these tiles, a map will be constructed using a Kriging procedure. 

Options for the "streetgreen.py" script can be obtained by navigating to the installation directory and typing:

```sh
./streetgreen.py --help
```

The most important option is to select the bounding box of the area to map, with `"-b/--bbox`. The bounding box "almere_amsterdam" includes nearly the whole coverage of the dataset.

The segmentation model can be selected through `-m/--model`. Currently, only pretrained models from [DeepLab](https://github.com/tensorflow/models/blob/master/research/deeplab/g3doc/model_zoo.md) are available for selection. Choose "deeplab-mobilenet" for fast inference and "deeplab-xception_71" for higher quality inference.

Process based parallelization is available through a combination of the `-n` and `-i` options, which distributes the 1km x 1km tiles over different jobs. For example if you have two machines, then on one you would run `-n 2 -i 0`, while you would give the other machine the `-n 2 -i 1` option. Then merging the tile data, you would have the complete data that you would get running with default options.

The resolution can be adjusted by using the `-l/--grid` options. Every level higher increases the spatial resolution of the map by a factor of 2, with the lowest being 1km x 1km, using the option `-l 0`.

Instead of sampling only once per grid point, the option `-y/--historical-data` allows for sampling of each available year at each grid point.

By default the program uses cubic pictures. With the `--panorama` option, panorama images are used instead, which takes less time, since only one instead of four pictures are analysed. But accuracy is expected to be reduced.

#### Individual picture analysis [seg_analysis.py]

Segmentation analysis of individual/arbitrary pictures/panoramas is available through the `seg_analysis.py` script. It takes a single argument: the picture to analyse. It will show the picture + the segmentation overlay in a new window.

#### Basic statistical comparison [comp_green.py]

To compare different "green" measures against each other, the `comp_green.py` script can be used. It computes a linear regression between different variables or the same variable but panoramic vs cubic pictures.


#### Temporal comparison [ time_compare.py ]

Compare points at the same location but different points in time with each other to observe trends of variations with regards to season, year, time of day.

## Application Programming Interface

There are several layers of abstraction to solve the problem of getting data, organizing files, and doing segmentation analyses. The recommended way is to use the tile manager, which ensures that the panoramas are divided into 1km x 1km tiles. This gives the benefit of possible parallelization, but also ensures that not too many pictures are placed in the same folder, and the amount of memory used is limited.

#### TileManager

To create an instance of a tile managers, one does the following:

```python
tile_man = TileManager(seg_model=DeepLabModel,
					 seg_kwargs={"model_name": "xception_71"}
					 green_model=ClassPercentage,
					 grid_level=1,
					 bbox=select_area("amsterdam"))
```

This creates a tile manager that organizes the data and pictures. By initializing the tile manager, the data is not automatically downloaded yet. There are two different ways to continue; the recommended way to obtain the greenery data is to use the `green_direct` method, which does all the steps in sequence. One advantage is that it will do each tile in sequence and clears the memory usage of temporary data:

```python
green_res = tile_man.green_direct()
```

One thing to keep in mind is that a lot of temporary data is stored/cached, so that it does not need to be recalculated every time. For example the segmentation of each picture is stored in a file such as `segments_cubic_deeplab_mobilenet.json`, which contains a gzip'ed segmentation array converted to base64 to make it portable/human readable, but also space efficient.

The functions will try to detect this file and not recompute it if it is already available. A next step would be to compute the vegetation percentages, which are also cached in a `green_res.json`, and include the WGS84 coordinates.

#### Visualization

The greenery can be plotted in a 2d contour plot by using either the "plot\_greenery" or the  or "krige\_map" method of the TileManager class.

```python
plot_greenery(green_res)
```

This procedure uses linear interpolation of the data points.

or create an HTML map (under data.amsterdam/maps/) overlayed on top of OpenStreetMap:

```python
tile_man.krige_map()
```

This procedure uses ordinary kriging, with currently an exponential variogram. For performance reasons, the kriging procedure is not applied to the data as a single block, but instead, stitched together from each tile. The variogram is computed from all points (but with sampling).

