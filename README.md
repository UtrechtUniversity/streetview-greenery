# streetview-greenery

Project to retrieve and process panoramic photo's and compute the greenery as perceived from street level.

## Description

The base idea of this package is to download panorama (or other) pictures of living/working area's and compute the greenness of that area. The first step is to do a segmentation analysis: assigning object classes to individual pixels. The second step is to convert these segmented pictures into a measure of greenness. The last step is to compute a map from individiual greenness measures.

## Example maps

Sampled map of Amsterdam/Almere: [link](https://qubixes.github.io/streetview-greenery/docs/adam_alm.html)

Detailed map of Muiderpoort region: [link](https://qubixes.github.io/streetview-greenery/docs/muiderpoort.html)

Detailed map of Gaasperdam region: [link](https://qubixes.github.io/streetview-greenery/docs/mijndenhof.html)

## Installation

There is at the moment no real installation script. Just make sure you have all the requirements below:

### Requirements / dependencies

- Python 3.6+
- Pillow
- numpy
- matplotlib
- tensorflow
- urllib
- pykrige
- scipy
- tqdm

## Quickstart

The script [__main__.py](__main__.py) is an example of how to do a simple greenery analysis.

#### Panorama Manager

The first step is to instance a panorama manager. The job of the panorama manager is to manage the collection of images/panorama's, which includes downloading/creating panorama's, handle errors, checking if the data already exists, etc. To instance the panorama manager, one needs to pass it the segmentation model + parameters, and greenery model + parameters.

```python
panoramas = AdamPanoramaManager(seg_model=DeepLabModel,
                                green_model=VegetationPercentage
)
```

Currently, there is only one data source implemented, which is the [data.amsterdam](http://data.amsterdam.nl) API. 

#### Loading meta-data

The second step is to load the meta-data into memory. This can be done from disk or downloaded from the internet. This data (and almost all other data) is automatically cached on disk. Parameters for this step is for example setting the borders of what to download:

```python 
cc = [52.299584, 4.971973]  # Degrees lattitude, longitude
# Radius of circle to download.
radius = 100  # meters
panoramas.get(center=cc, radius=radius)
```

#### (Down)loading panorama data into memory

The third step is to load the actual panorama's into memory. This is done using the meta data of the previous step. As a parameter one can set the number of samples that are taken. Any pictures not sampled are not downloaded. The process is seeded such that always the same pictures are loaded.

```python
panoramas.load(n_sample=1000)
```

#### Segmentation analysis

The next step is to do the segmentation analysis for each picture. Currently there is a single model implemented, which is a pre-trained DeepLab model (from [here](https://github.com/tensorflow/models/blob/master/research/deeplab/g3doc/model_zoo.md)). Currently only the MobileNet-v2 version is available, which offers fast inference time (but relatively poor performance). The model is based on the City Scapes data set.

```python
panoramas.seg_analysis()
```

#### Greenery analysis

Greenery analysis is done at the next step. At the moment with the City Scapes dataset, greenery analysis is simply finding the percentage of pixels assigned to the class "vegetation".

```python
green_res = panoramas.green_analysis()
```

The function gives back a dictionary with the greenery measure, longitude and lattitude coordinates.

#### Visualization

The greenery can be plotted in a 2d contour plot by using either the "plot\_greenery" or "plot\_green\_krige" functions. The first uses simple linear interpolation to generate a contour plot. The second uses ordinary kriging (variogram=spherical) to get a better estimate. The latter also creates an overlay for Open Streetmap, which can be viewed by opening index.html.

```python
plot_green_krige(green_res)
```
