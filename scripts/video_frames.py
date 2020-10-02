#!/usr/bin/env python


import cv2
import sys


def main(video_fp):
    cap = cv2.VideoCapture(video_fp)
    length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, 123)
    success, image = cap.read()
    cv2.imwrite(f"frame.jpg", image)
#     success, image = cap.read()
    print(success)
#     with open("test.jpg", "wb") as f:
#         f.write(image)
    print(length)

if __name__ == "__main__":
    main(video_fp=sys.argv[1])
