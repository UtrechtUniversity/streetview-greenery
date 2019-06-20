#!/usr/bin/env python

import folium
import numpy as np
import json
from json.decoder import JSONDecodeError
import gdal
import osr
import osgeo.ogr as ogr


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

    def load(self, file_fp):
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
        proj = osr.SpatialReference()
        proj.ImportFromEPSG(4326)
        driver = gdal.GetDriverByName("GTiff")
        [rows, cols] = self.greenery.shape
        print(file_fp, rows, cols)
        geodata = driver.Create(file_fp, rows, cols, 1, eType=gdal.GDT_Float32)
        xmin = self.long_grid.min()
        xres = (self.long_grid.max()-self.long_grid.min())/(self.long_grid.shape[0])
        yres = (self.lat_grid.max()-self.lat_grid.min())/(self.lat_grid.shape[0])
        ymin = self.lat_grid.min()
        geotransform = (
            xmin, xres, 0, ymin, 0, yres
        )
        geodata.SetGeoTransform(geotransform)
        geodata.SetProjection(proj.ExportToWkt())
        alpha_zero = np.where(self.alpha_map == 0)
        new_green_map = np.copy(self.greenery)
        new_green_map[alpha_zero] = 99999
        geodata.GetRasterBand(1).WriteArray(new_green_map)
        geodata.GetRasterBand(1).SetNoDataValue(99999)
        geodata.FlushCache()


def _lat_bounds(lat_grid, long_grid):
    bounds = [
        [
            lat_grid.min(),
            long_grid.min(),
        ],
        [
            lat_grid.max(),
            long_grid.max(),
        ]
    ]
    return bounds


def _cmap2rgb(step, cmap="gist_rainbow"):
    from matplotlib import cm
    return getattr(cm, cmap)(step, bytes=True)


def green_map_to_img(green_i, alpha_i, min_green, max_green, cmap="gist_rainbow"):
    delta = (max_green-min_green)
    nx = green_i.shape[0]
    ny = green_i.shape[1]

    green_rgba = np.zeros(green_i.shape+(4,), dtype=np.uint8)
    for irow, row in enumerate(green_i):
        for icol, col in enumerate(row):
            if col < min_green or col > max_green:
                green_rgba[nx-irow-1][icol] = np.zeros(4)
            else:
                step = int(256*(col-min_green)/delta)
                green_rgba[nx-irow-1][icol] = np.array(_cmap2rgb(step, cmap))
                if alpha_i is not None:
                    alpha = alpha_i[irow][icol]
                    green_rgba[nx-irow-1][icol][3] = 255*alpha

    return green_rgba


def create_map(green_layers, html_file="index.html"):
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
            look_at = [lat_grid.mean(), long_grid.mean()]
            m = folium.Map(location=look_at, zoom_start=15, control_scale=True)

        green_rgba = green_map_to_img(green_i, alpha_i, min_green, max_green, cmap)
        folium.raster_layers.ImageOverlay(
            green_rgba, mercator_project=True, opacity=0.5,
            bounds=_lat_bounds(lat_grid, long_grid),
            name=name
        ).add_to(m)
    folium.LayerControl().add_to(m)
    m.save(html_file)


def green_res_to_shp(green_res, green_key, shape_fp):
    driver = ogr.GetDriverByName("ESRI Shapefile")
    data_source = driver.CreateDataSource(shape_fp)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    layer = data_source.CreateLayer("greenery", srs, ogr.wkbPoint)
    layer.CreateField(ogr.FieldDefn(green_key, ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("Latitude", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("Longitude", ogr.OFTReal))

    for i in range(len(green_res["green"])):
        feature = ogr.Feature(layer.GetLayerDefn())
        green = green_res["green"][i]
        lat = green_res["lat"][i]
        long = green_res["long"][i]

        feature.SetField(green_key, green)
        feature.SetField("Latitude", lat)
        feature.SetField("Longitude", long)

        point = ogr.CreateGeometryFromWkt(f"Point({long} {lat})")
        feature.SetGeometry(point)
        layer.CreateFeature(feature)
        feature = None

    data_source = None


def _empty_green_res():
    green_res = {
        "green": [],
        "lat": [],
        "long": [],
    }
    return green_res


def _extend_green_res(g1, g2):
    if "green" in g2 and "green" in g1:
        for key in g1:
            g1[key].extend(g2[key])
