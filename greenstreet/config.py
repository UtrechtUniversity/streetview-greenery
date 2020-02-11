PICTURE_NAMES = {
    "adam-panorama": ["adam-panorama.jpg"],
    "adam-cubic": ["adam-front.jpg", "adam-back.jpg", "adam-left.jpg",
                   "adam-right.jpg"],
}

INV_PICTURE_NAMES = {}
for pic_type, files in PICTURE_NAMES.items():
    INV_PICTURE_NAMES.update({file: pic_type for file in files})

STATUS_OK = 0
STATUS_FAIL = 1
