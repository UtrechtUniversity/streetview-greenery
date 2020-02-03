#!/usr/bin/env python


from greenstreet import TileManager

if __name__ == "__main__":
    tile_man = TileManager("output/oosterpark/tiles", bbox_str="oosterpark",
                           grid_level=0, use_panorama=True)
    tile_man.download()
    tile_man.meta_summary()
