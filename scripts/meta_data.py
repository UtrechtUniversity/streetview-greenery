#!/usr/bin/env python


from greenstreet import TileManager

if __name__ == "__main__":
    tile_man = TileManager("../../output/oosterpark", bbox_str="oosterpark",
                           grid_level=1, use_panorama=False,
                           weighted_panorama=False)
    tile_man.query()
    tile_man.download()
    tile_man.segmentation()
    tile_man.greenery()
    par, res, krige_dir = tile_man.compute_semivariance()
    tile_man.compute_krige(par, res, krige_dir)
