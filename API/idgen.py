def get_green_key(myclass, seg_id, green_id, grid_level=None):
    key = ""
    key += f"{green_id}-{seg_id}-"

    if myclass.__name__ == "AdamPanorama":
        key += "panorama"
    elif myclass.__name__ == "AdamPanoramaCubic":
        key += "cubic"
    else:
        key += "unknown"

    if grid_level is not None:
        key += f"-lvl_{grid_level}"
    return key
