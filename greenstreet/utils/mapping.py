#!/usr/bin/env python

import json
from json.decoder import JSONDecodeError
from pathlib import Path
import folium
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from tqdm import tqdm


class MapImageOverlay:
    "Overlay that can be plotted over a street map. Assumes WGS 84."
    def __init__(self, greenery, lat_grid=None, long_grid=None, alpha_map=None,
                 min_green=0.0, max_green=0.75, cmap="gist_rainbow", name=None):
        if isinstance(greenery, str):
            self.load(greenery)
        else:
            self.greenery = greenery
            self.alpha_map = alpha_map
            self.lat_grid = lat_grid
            self.long_grid = long_grid
            self.min_green = min_green
            self.max_green = max_green
            self.cmap = cmap
            self.name = name
        self.dlat = (self.lat_grid.max()-self.lat_grid.min())/(len(self.lat_grid)-1)
        self.dlong = (self.long_grid.max()-self.long_grid.min())/(len(self.long_grid)-1)

    def __str__(self):
        mystr = "\n--------- Map Overlay ----------\n"
        mystr += f"Name: {self.name}\n"
        mystr += f"Lattitude: [{self.lat_grid.min()}, {self.lat_grid.max()}]\n"
        mystr += f"Longitude: [{self.long_grid.min()}, {self.long_grid.max()}]\n"
        mystr += f"Values: [{self.greenery.min()}, {self.greenery.max()}]\n"
        mystr += f"Alpha (avg): {self.alpha_map.mean()}\n"
        mystr += "---------------------------------\n"
        return mystr

    def load(self, file_fp):
        "Load the overlay from a .json file."
        try:
            with open(file_fp, "r") as f:
                gr_dict = json.load(f)
        except JSONDecodeError:
            raise FileNotFoundError(f"Error reading file {file_fp}")
        self.greenery = np.array(gr_dict['greenery'])
        if 'alpha_map' in gr_dict:
            self.alpha_map = np.array(gr_dict['alpha_map'])
        else:
            self.alpha_map = None
        self.lat_grid = np.array(gr_dict['lat_grid'])
        self.long_grid = np.array(gr_dict['long_grid'])
        self.min_green = gr_dict['min_green']
        self.max_green = gr_dict['max_green']
        self.cmap = gr_dict['cmap']
        self.name = gr_dict['name']

    def save(self, file_fp):
        "Save the overlay to a .json file."
        gr_dict = {}
        gr_dict['greenery'] = self.greenery.tolist()
        if self.alpha_map is not None:
            gr_dict['alpha_map'] = self.alpha_map.tolist()
        gr_dict['lat_grid'] = self.lat_grid.tolist()
        gr_dict['long_grid'] = self.long_grid.tolist()
        gr_dict['min_green'] = self.min_green
        gr_dict['max_green'] = self.max_green
        gr_dict['cmap'] = self.cmap
        gr_dict['name'] = self.name

        with open(file_fp, "w") as f:
            json.dump(gr_dict, f, indent=2)

    def write_geotiff(self, file_fp):
        "Write the map overlay to a geoTiff file."

        import gdal
        import osr

        # Assume that internal coordinates are WGS 84.
        proj = osr.SpatialReference()
        proj.ImportFromEPSG(4326)
        driver = gdal.GetDriverByName("GTiff")
        [rows, cols] = self.greenery.shape
        geodata = driver.Create(file_fp, cols, rows, 1, eType=gdal.GDT_Float32)
        xmin = self.long_grid.min()
        xres = (self.long_grid.max()-self.long_grid.min())/(self.long_grid.shape[0])
        yres = (self.lat_grid.max()-self.lat_grid.min())/(self.lat_grid.shape[0])
        ymin = self.lat_grid.min()
        geotransform = (
            xmin, xres, 0, ymin, 0, yres
        )

        geodata.SetGeoTransform(geotransform)
        geodata.SetProjection(proj.ExportToWkt())

        # For transparent pictures, set them to no data in the tiff file.
        alpha_zero = np.where(self.alpha_map == 0)
        new_green_map = self.greenery.astype('float32')
        new_green_map[alpha_zero] = 99999
        geodata.GetRasterBand(1).WriteArray(new_green_map)
        geodata.GetRasterBand(1).SetNoDataValue(99999)
        geodata.FlushCache()

    def get_green(self, lat, long):
#         print(self.dlat)
#         print((lat-self.lat_grid.min())/self.dlat)
        i_lat = int(round((lat-self.lat_grid.min())/self.dlat))
        i_long = int(round((long-self.long_grid.min())/self.dlong))
        if (i_lat < 0 or i_lat >= len(self.lat_grid) 
            or i_long < 0 or i_long >= len(self.long_grid)
            or self.alpha_map[i_lat, i_long] == 0):
            return None
#         print(i_lat, i_long)
        return self.greenery[i_lat, i_long]

    def compare(self, overlay):
        green_self = []
        green_overlay = []
        for lat in tqdm(self.lat_grid):
            for long in self.long_grid:
                sg = self.get_green(lat, long)
                if sg is None or sg < 0 or sg > 1:
                    continue
                og = overlay.get_green(lat, long)
                if og is None or og < 0 or og > 1:
                    continue
                green_self.append(sg)
                green_overlay.append(og)
        
        green_self = np.array(green_self)
        green_overlay = np.array(green_overlay)
        reg = LinearRegression().fit(green_self.reshape(-1,1), green_overlay)
        reg_score = reg.score(green_self.reshape(-1,1), green_overlay)
        print("score", reg_score)
        print("coef, intercept", reg.coef_[0], reg.intercept_)
        reg_lab = "{0:.2f} + {1:.2f} x (score={2:.2f})".format(reg.intercept_, reg.coef_[0],
                                                               reg_score)
        plt.plot([0.0, 0.7], reg.predict([[0.0], [0.7]]), label=reg_lab)
        plt.scatter(green_self, green_overlay, alpha=0.1)
        plt.xlabel("Streetview")
        plt.ylabel("NDVI")
        plt.legend(loc="lower right")
        plt.show()

    @classmethod
    def from_krige_dir(cls, krige_dir, *args, **kwargs):
        index_fp = Path(krige_dir, "index.json")
        with open(index_fp, "r") as f:
            index_data = json.load(f)

        lat_grid = np.array(index_data["lat_grid"])
        long_grid = np.array(index_data["long_grid"])
        tile_matrix = np.array(index_data["tile_matrix"])
        greenery = np.zeros((len(lat_grid), len(long_grid)))
        for i_lat, i_long in np.ndindex(tile_matrix.shape):
            krige_fp = Path(krige_dir, tile_matrix[i_lat, i_long] + ".json")
            with open(krige_fp, "r") as f:
                krige_data = json.load(f)
            data = np.array(krige_data["data"])
            j_lat_min = i_lat*data.shape[0]
            j_long_min = i_long*data.shape[1]
            greenery[j_lat_min:j_lat_min+data.shape[0],
                     j_long_min:j_long_min+data.shape[1]] = data
        try:
            with open(Path(krige_dir, "alpha.json"), "r") as f:
                alpha = np.array(json.load(f))
        except FileNotFoundError:
            alpha = None
        return cls(greenery, lat_grid, long_grid, alpha, *args, **kwargs)


def _lat_bounds(lat_grid, long_grid):
    "Create lattice bounds from the grid."
    dlat = (lat_grid.max() - lat_grid.min())/(len(lat_grid)-1)
    dlong = (long_grid.max() - long_grid.min())/(len(long_grid)-1)
    bounds = [
        [
            lat_grid.min()-0.5*dlat,
            long_grid.min()-0.5*dlong,
        ],
        [
            lat_grid.max()+0.5*dlat,
            long_grid.max()+0.5*dlong,
        ]
    ]
    return bounds


def _cmap2rgb(step, cmap="gist_rainbow"):
    "Get a RGB color from a color map from a step in [0,255]."
    from matplotlib import cm
    return getattr(cm, cmap)(step, bytes=True)


def green_map_to_img(green_i, alpha_i, min_green, max_green,
                     cmap="gist_rainbow"):
    """ Create an RGB image from a greenery map.

    Arguments:
    ----------
    green_i: np.array
        2D Array of all greenery values.
    alpha_i: np.array
        2D Array of transparency [alpha] values with same shape.
    min_green: float
        Lowest value for greenery measure. Anything below is transparent.
    max_green: float
        Highest value for greenery measure. Anything above is transparent.
    cmap: str
        Color map to use for map [see matplotlib documentation for choices].
    """
    delta = (max_green-min_green)
    nx = green_i.shape[0]
    ny = green_i.shape[1]

    green_rgba = np.zeros(green_i.shape+(4,), dtype=np.uint8)
    for irow, row in enumerate(green_i):
        for icol, col in enumerate(row):
            # The rows should be in reverse order.
            if col < min_green or col > max_green:
                green_rgba[nx-irow-1][icol] = np.zeros(4)
            else:
                # Convert green value into something in [0, 255]
                step = int(256*(col-min_green)/delta)
                green_rgba[nx-irow-1][icol] = np.array(_cmap2rgb(step, cmap))
                if alpha_i is not None:
                    alpha = alpha_i[irow][icol]
                    green_rgba[nx-irow-1][icol][3] = 255*alpha

    return green_rgba


def create_map(green_layers, results, html_file="index.html"):
    """ Create an HTML map from map overlays.

    Arguments:
    ----------
    green_layers: list, MapOverlay
        Either a single overlay or a list of overlays.
    html_file:
        Destination file for HTML map.
    """
    if isinstance(green_layers, MapImageOverlay):
        green_layers = [green_layers]

    for i, gr_layer in enumerate(green_layers):
        green_i = gr_layer.greenery
        alpha_i = gr_layer.alpha_map
        lat_grid = gr_layer.lat_grid
        long_grid = gr_layer.long_grid
        min_green = gr_layer.min_green
        max_green = gr_layer.max_green
        cmap = gr_layer.cmap
        name = gr_layer.name

        if i == 0:
            # Initialize map
            look_at = [lat_grid.mean(), long_grid.mean()]
            m = folium.Map(location=look_at, zoom_start=15, control_scale=True)

        green_rgba = green_map_to_img(green_i, alpha_i, min_green, max_green, cmap)
        folium.raster_layers.ImageOverlay(
            green_rgba, mercator_project=True, opacity=0.5,
            bounds=_lat_bounds(lat_grid, long_grid),
            name=name
        ).add_to(m)
    for tile in results.values():
        for i in range(len(tile['latitude'])):
            folium.vector_layers.Circle(
                (tile['latitude'][i], tile['longitude'][i]),
                radius=3, popup=tile['data'][i]).add_to(m)
    folium.LayerControl().add_to(m)
    m.save(str(html_file))


def green_res_to_shp(green_res, green_key, shape_fp):
    " Convert greenery measurements to shape file. "
    import osgeo.ogr as ogr
    import osr

    driver = ogr.GetDriverByName("ESRI Shapefile")
    data_source = driver.CreateDataSource(shape_fp)

    # Internal coordinates are WGS 84
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)

    layer = data_source.CreateLayer("greenery", srs, ogr.wkbPoint)
    layer.CreateField(ogr.FieldDefn(green_key, ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("Latitude", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("Longitude", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("Timestamp"), ogr.OFTDateTime)

    for i in range(len(green_res["green"])):
        feature = ogr.Feature(layer.GetLayerDefn())
        green = green_res["green"][i]
        lat = green_res["lat"][i]
        long = green_res["long"][i]
        timestamp = green_res["timestamp"][i]

        feature.SetField(green_key, green)
        feature.SetField("Latitude", lat)
        feature.SetField("Longitude", long)
        feature.SetField("Timestamp", timestamp)

        # Add point geometry.
        point = ogr.CreateGeometryFromWkt(f"Point({long} {lat})")
        feature.SetGeometry(point)
        layer.CreateFeature(feature)
        feature = None

    # Close/write to file.
    data_source = None


def _get_lat(results):
    lat = []
    for x in results.values():
        lat.extend(x["latitude"])
    return np.array(lat)
#     return np.concatenate([np.array(x["latitude"]) for x in results.values()]).reshape(-1)


def _get_long(results):
    long = []
    for x in results.values():
        long.extend(x["longitude"])
    return np.array(long)


def compute_alpha(results, lat_grid, long_grid, pixel_dist=5):
    lat = _get_lat(results)
    long = _get_long(results)
    all_coor = np.vstack((lat, long)).T
    dlat = lat_grid[1] - lat_grid[0]
    dlong = long_grid[1] - long_grid[0]

    lat_start = np.array([lat_grid[0], long_grid[0]])
    dl = np.array([dlat, dlong])
    alpha = np.zeros((len(lat_grid), len(long_grid)))

    for coor in all_coor:
        coor_base = (coor - lat_start)/dl
        coor_min = coor - 5*dl
        coor_max = coor + 5*dl
        i_min = np.ceil((coor_min - lat_start)/dl)
        i_max = np.floor((coor_max - lat_start)/dl)
        i_min[i_min < 0] = 0
        i_max[0] = min(alpha.shape[0]-1, i_max[0])
        i_max[1] = min(alpha.shape[1]-1, i_max[1])

        i_min = np.array(i_min, dtype=int)
        i_max = np.array(i_max, dtype=int)
        for i_lat in range(i_min[0], i_max[0]):
            lat_pix = i_lat - coor_base[0]
            for i_long in range(i_min[1], i_max[1]):
                long_pix = i_long - coor_base[1]
                d_pix = np.sqrt(lat_pix**2 + long_pix**2)
                if d_pix < pixel_dist:
                    alpha[i_lat, i_long] = 1
    return alpha


def _empty_green_res():
    green_res = {
        "green": [],
        "lat": [],
        "long": [],
        "timestamp": [],
        "pano_id": [],
    }
    return green_res


def _add_green_res(green_res, new_val, panorama):
    green_res["green"].append(new_val)
    green_res["lat"].append(panorama.latitude)
    green_res["long"].append(panorama.longitude)
    green_res["timestamp"].append(panorama.timestamp)
    green_res["pano_id"].append(panorama.id)


def _extend_green_res(g1, g2):
    if "green" in g2 and "green" in g1:
        for key in g1:
            g1[key].extend(g2[key])
