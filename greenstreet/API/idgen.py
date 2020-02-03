

def get_green_key(data_source, green_measure, seg_model, use_panorama=False,
                  grid_level=None,
                  all_years=False):
    key = ""
    key += f"{data_source}-{green_measure}-{seg_model}-"

    if use_panorama:
        key += "panorama"
    else:
        key += "cubic"

    if grid_level is not None:
        key += f"-lvl_{grid_level}"

    if all_years:
        key += f"-historical"
    return key
