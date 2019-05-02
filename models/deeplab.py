'''
Based on https://github.com/tensorflow/models/blob/master/research/
                /deeplab/deeplab_demo.ipynb

'''

import os
from io import BytesIO
import tarfile
from six.moves import urllib

from matplotlib import gridspec
from matplotlib import pyplot as plt
import numpy as np
from PIL import Image

import tensorflow as tf
from models.labels import labels


def _get_model(model_name):
    model_dir = "pre_trained_models"
#     model_url = "http://download.tensorflow.org/models/"\
#                 "deeplabv3_mnv2_cityscapes_train_2018_02_05.tar.gz"

    url_prefix = 'http://download.tensorflow.org/models/'

    if model_name == "mobilenet":
        tar_file = "deeplabv3_mnv2_cityscapes_train_2018_02_05.tar.gz"
    else:
        raise ValueError(f"Error: model {model_name} unknown")

    model_url = url_prefix+tar_file
    tar_fp = os.path.join(model_dir, tar_file)
    if not os.path.exists(tar_fp):
        os.makedirs(model_dir, exist_ok=True)
        print('Downloading model...')
        urllib.request.urlretrieve(model_url, tar_fp)
        print('Download completed.')
    return tar_fp


class DeepLabModel(object):
    """Class to load deeplab model and run inference."""

    INPUT_TENSOR_NAME = 'ImageTensor:0'
    OUTPUT_TENSOR_NAME = 'SemanticPredictions:0'
    INPUT_SIZE = 513
    FROZEN_GRAPH_NAME = 'frozen_inference_graph'

    def __init__(self, model_name="mobilenet"):
        """Creates and loads pretrained deeplab model."""
        self.graph = tf.Graph()
        self.sess = None
        self.load(model_name)
        self.load_segmentation_scheme()

    def load(self, model_name):
        # Extract frozen graph from tar archive.
        tarball_fp = _get_model(model_name)
        tar_file = tarfile.open(tarball_fp)
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

    def load_segmentation_scheme(self):
        self.label_names = []
        self.label_colors = []

        for label in labels:
            if label.trainId != 255:
                self.label_names.append(label.name)
                self.label_colors.append(list(label.color))
        self.label_names = np.asarray(self.label_names)
        self.label_colors = np.asarray(self.label_colors)
        self.color_map = (self.label_names, self.label_colors)

    def run(self, image_fp):
        """Runs inference on a single image.

        Args:
            image: A PIL.Image object, raw input image.

        Returns:
            resized_image: RGB image resized from original input image.
            seg_map: Segmentation map of `resized_image`.
        """
        with open(image_fp, "rb") as f:
            jpeg_str = f.read()
        image = Image.open(BytesIO(jpeg_str))
        print('running deeplab on image %s...' % image_fp)

        width, height = image.size
        resize_ratio = 1.0 * self.INPUT_SIZE / max(width, height)
        target_size = (int(resize_ratio * width), int(resize_ratio * height))
        resized_image = image.convert('RGB').resize(target_size, Image.ANTIALIAS)
        batch_seg_map = self.sess.run(
            self.OUTPUT_TENSOR_NAME,
            feed_dict={self.INPUT_TENSOR_NAME: [np.asarray(resized_image)]})
        seg_map = batch_seg_map[0]
        return resized_image, seg_map, self.color_map


def plot_segmentation(image, seg_map, color_map):
    """Visualizes input image, segmentation map and overlay view."""

    label_names = color_map[0]
    label_colors = color_map[1]

    plt.figure(figsize=(15, 5))
    grid_spec = gridspec.GridSpec(1, 4, width_ratios=[6, 6, 6, 1])

    plt.subplot(grid_spec[0])
    plt.imshow(image)
    plt.axis('off')
    plt.title('input image')

    plt.subplot(grid_spec[1])
    seg_image = label_colors[seg_map].astype(np.uint8)
    plt.imshow(seg_image)
    plt.axis('off')
    plt.title('segmentation map')

    plt.subplot(grid_spec[2])
    plt.imshow(image)
    plt.imshow(seg_image, alpha=0.7)
    plt.axis('off')
    plt.title('segmentation overlay')

    unique_labels = np.unique(seg_map)
    ax = plt.subplot(grid_spec[3])
    img_colors = np.reshape(label_colors[unique_labels], (-1, 1, 3))
    plt.imshow(img_colors.astype(np.uint8), interpolation='nearest')
    ax.yaxis.tick_right()
    plt.yticks(range(len(unique_labels)), label_names[unique_labels])
    plt.xticks([], [])
    ax.tick_params(width=0.0)
    plt.grid(False)
    plt.show()


# MODEL = DeepLabModel(download_path)
# print('model loaded successfully!')

# img_fp = "../data.amsterdam/pics/pano_0002_003645.jpg"


# def run_visualization(img_fp):
#     """Inferences DeepLab model and visualizes result."""
#     resized_im, seg_map = MODEL.run(original_im)

#     vis_segmentation(resized_im, seg_map)


# run_visualization(img_fp)


