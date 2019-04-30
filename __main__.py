from API.data_amsterdam import PanoramaAmsterdam


def main():
    panoramas = PanoramaAmsterdam()
    cc = [52.3023958, 4.9928061]
    radius = 20
    panoramas.get(center=cc, radius=radius)
    panoramas.print_panoramas()
    panoramas.download()
#     print(panoramas)


if __name__ == "__main__":
    main()
