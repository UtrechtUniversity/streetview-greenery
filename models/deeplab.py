'''
Created on 1 May 2019

@author: qubix
'''

import os
from io import BytesIO
import tarfile
import tempfile
from six.moves import urllib

from matplotlib import gridspec
from matplotlib import pyplot as plt
import numpy as np
from PIL import Image

import tensorflow as tf
import labels


class DeepLabModel(object):
    """Class to load deeplab model and run inference."""

    INPUT_TENSOR_NAME = 'ImageTensor:0'
    OUTPUT_TENSOR_NAME = 'SemanticPredictions:0'
    INPUT_SIZE = 513
    FROZEN_GRAPH_NAME = 'frozen_inference_graph'

    def __init__(self, tarball_path):
        """Creates and loads pretrained deeplab model."""
        self.graph = tf.Graph()

        graph_def = None
        # Extract frozen graph from tar archive.
        tar_file = tarfile.open(tarball_path)
        for tar_info in tar_file.getmembers():
            if self.FROZEN_GRAPH_NAME in os.path.basename(tar_info.name):
                file_handle = tar_file.extractfile(tar_info)
                graph_def = tf.GraphDef()
                graph_def.ParseFromString(file_handle.read())
                break

        tar_file.close()

        if graph_def is None:
            raise RuntimeError('Cannot find inference graph in tar archive.')

        with self.graph.as_default():
            tf.import_graph_def(graph_def, name='')

        self.sess = tf.Session(graph=self.graph)

    def run(self, image):
        """Runs inference on a single image.

        Args:
            image: A PIL.Image object, raw input image.

        Returns:
            resized_image: RGB image resized from original input image.
            seg_map: Segmentation map of `resized_image`.
        """
        width, height = image.size
        resize_ratio = 1.0 * self.INPUT_SIZE / max(width, height)
        target_size = (int(resize_ratio * width), int(resize_ratio * height))
        resized_image = image.convert('RGB').resize(target_size, Image.ANTIALIAS)
        batch_seg_map = self.sess.run(
            self.OUTPUT_TENSOR_NAME,
            feed_dict={self.INPUT_TENSOR_NAME: [np.asarray(resized_image)]})
        seg_map = batch_seg_map[0]
        return resized_image, seg_map


def label_to_color_image(label):
    """Adds color defined by the dataset colormap to the label.

    Args:
        label: A 2D array with integer type, storing the segmentation label.

    Returns:
        result: A 2D array with floating type. The element of the array
        is the color indexed by the corresponding element in the input label
        to the PASCAL color map.

  Raises:
    ValueError: If label is not of rank 2 or its value is larger than color
      map maximum entry.
  """
    if label.ndim != 2:
        raise ValueError('Expect 2-D input label')

    return FLAT_LABEL_COLORS[label]


def vis_segmentation(image, seg_map):
    """Visualizes input image, segmentation map and overlay view."""

    plt.figure(figsize=(15, 5))
    grid_spec = gridspec.GridSpec(1, 4, width_ratios=[6, 6, 6, 1])

    plt.subplot(grid_spec[0])
    plt.imshow(image)
    plt.axis('off')
    plt.title('input image')

    plt.subplot(grid_spec[1])
    seg_image = label_to_color_image(seg_map).astype(np.uint8)
    plt.imshow(seg_image)
    plt.axis('off')
    plt.title('segmentation map')

    plt.subplot(grid_spec[2])
    plt.imshow(image)
    plt.imshow(seg_image, alpha=0.7)
    plt.axis('off')
    plt.title('segmentation overlay')

    unique_labels = np.unique(seg_map)
#     print(seg_map)
    ax = plt.subplot(grid_spec[3])
    plt.imshow(
       LABEL_COLORS[unique_labels].astype(np.uint8), interpolation='nearest')
    ax.yaxis.tick_right()
    plt.yticks(range(len(unique_labels)), LABEL_NAMES[unique_labels])
    plt.xticks([], [])
    ax.tick_params(width=0.0)
    plt.grid(False)
    plt.show()


LABEL_NAMES = []
LABEL_COLORS = []
FLAT_LABEL_COLORS = []

for label in labels.labels:
    if label.trainId != 255:
        LABEL_NAMES.append(label.name)
        LABEL_COLORS.append([list(label.color)])
        FLAT_LABEL_COLORS.append(list(label.color))

LABEL_NAMES = np.asarray(LABEL_NAMES)
LABEL_COLORS = np.asarray(LABEL_COLORS)
FLAT_LABEL_COLORS = np.asarray(FLAT_LABEL_COLORS)

model_url = "http://download.tensorflow.org/models/"\
            "deeplabv3_mnv2_cityscapes_train_2018_02_05.tar.gz"

_DOWNLOAD_URL_PREFIX = 'http://download.tensorflow.org/models/'

_TARBALL_NAME = 'deeplab_model.tar.gz'
model_dir = "pre_trained_models"

download_path = os.path.join(model_dir, _TARBALL_NAME)
if not os.path.exists(download_path):
    print('downloading model, this might take a while...')
    urllib.request.urlretrieve(model_url,
                               download_path)
    print('download completed! loading DeepLab model...')

MODEL = DeepLabModel(download_path)
print('model loaded successfully!')

img_fp = "../data.amsterdam/pics/pano_0002_003645.jpg"


def run_visualization(img_fp):
    """Inferences DeepLab model and visualizes result."""
    with open(img_fp, "rb") as f:
        jpeg_str = f.read()
    original_im = Image.open(BytesIO(jpeg_str))

    print('running deeplab on image %s...' % img_fp)
    resized_im, seg_map = MODEL.run(original_im)

    vis_segmentation(resized_im, seg_map)


run_visualization(img_fp)


