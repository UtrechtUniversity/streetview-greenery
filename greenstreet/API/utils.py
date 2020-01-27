def get_tile_class(tile_type="adam"):
    from greenstreet.API.adam.tile import AdamPanoramaTile
    tile_dict = {
        "adam": AdamPanoramaTile,
    }

    try:
        return tile_dict[tile_type]
    except KeyError:
        raise ValueError(f"Tile type '{tile_type}' is unknown.")
