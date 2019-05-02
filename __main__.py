from API.data_amsterdam import PanoramaAmsterdam
from models.deeplab import DeepLabModel


def main():
    panoramas = PanoramaAmsterdam()
#     cc = [52.3023958, 4.9928061]
    cc = [52.299584, 4.971973]
    radius = 20  # meters
    panoramas.get(center=cc, radius=radius)
    panoramas.download()
    panoramas.seg_analysis(model=DeepLabModel)
    panoramas.show(model=DeepLabModel)


if __name__ == "__main__":
    main()
