from API.data_amsterdam import PanoramaAmsterdam
from models.deeplab import DeepLabModel, plot_segmentation


def main():
    panoramas = PanoramaAmsterdam()
    cc = [52.3023958, 4.9928061]
    radius = 20  # meters
    panoramas.get(center=cc, radius=radius)
    panoramas.download()
    files = panoramas.file_names()

    model = DeepLabModel()
    segmentation = model.run(files[1])
    plot_segmentation(*segmentation)


if __name__ == "__main__":
    main()
