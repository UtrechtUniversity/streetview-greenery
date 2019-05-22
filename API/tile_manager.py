from math import cos, pi, ceil, floor
from API.adam_tile import AdamPanoramaTile


def _extend_green_res(g1, g2):
    for key in g1:
        g1[key].extend(g2[key])


class TileManager(object):
    def __init__(self, resolution=500, bbox=None, grid_level=1, **kwargs):
        NL_bbox = [
            [50.803721015, 3.31497114423],
            [53.5104033474, 7.09205325687]
        ]

        if bbox is None:
            bbox = NL_bbox

        x_start = NL_bbox[0][1]
        x_end = NL_bbox[1][1]
        y_start = NL_bbox[0][0]
        y_end = NL_bbox[1][0]

        R_earth = 6356e3  # meters
        dy_target = 180*resolution/(R_earth*pi)
        dx_target = dy_target/cos(pi*(y_start+y_end)/360.0)

        nx = ceil((x_end-x_start)/dx_target)
        ny = ceil((y_end-y_start)/dy_target)

        dx = (x_end-x_start)/nx
        dy = (y_end-y_start)/ny

        i_min_x = floor((bbox[0][1]-x_start)/dx)
        i_max_x = ceil((bbox[1][1]-x_start)/dx)

        i_min_y = floor((bbox[0][0]-y_start)/dy)
        i_max_y = ceil((bbox[1][0]-y_start)/dy)

        print(f"({i_min_x}, {i_min_y}) -> ({i_max_x}, {i_max_y})")
        self.tile_list = []
        for ix in range(i_min_x, i_max_x):
            for iy in range(i_min_y, i_max_y):
                cur_bbox = [
                    [y_start+iy*dy, x_start+ix*dx],
                    [y_start+(iy+1)*dy, x_start+(ix+1)*dx]
                ]
                tile_name = f"NL_tile_{iy}_{ix}"
                tile = AdamPanoramaTile(tile_name=tile_name, bbox=cur_bbox,
                                        **kwargs)
                self.tile_list.append(tile)

        self.grid_level = grid_level

    def get(self, **kwargs):
        for tile in self.tile_list:
            tile.get(**kwargs)

    def load(self, **kwargs):
        for tile in self.tile_list:
            tile.load(grid_level=self.grid_level, **kwargs)

    def seg_analysis(self, **kwargs):
        for tile in self.tile_list:
            tile.seg_analysis(**kwargs)

    def green_analysis(self, **kwargs):
        green_res = {
            "green": [],
            "lat": [],
            "long": [],
        }

        for tile in self.tile_list:
            new_green_res = tile.green_analysis(**kwargs)
            _extend_green_res(green_res, new_green_res)
        return green_res
