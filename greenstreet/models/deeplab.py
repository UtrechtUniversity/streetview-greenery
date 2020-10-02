'''
Defines the class to load a pre-trained model from the DeepLab project.
The models are trained on the City-scapes dataset, with their trainId's.

Based on https://github.com/tensorflow/models/blob/master/research/
                /deeplab/deeplab_demo.ipynb

'''

import os
from io import BytesIO
import tarfile
from six.moves import urllib
import operator

from matplotlib import gridspec
from matplotlib import pyplot as plt
import numpy as np
from PIL import Image

from greenstreet.models.city_scapes import labels as cs_labels

try:
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    import logging
    logging.getLogger("tensorflow").setLevel(logging.ERROR)
    import tensorflow.compat.v1 as tf

    tf.disable_v2_behavior()
    tf.logging.set_verbosity(tf.logging.ERROR)
except ImportError:
    import tensorflow as tf


def _get_model(model_name):
    """ Download/find a DeepLab model from an abbreviated model_name. """
    model_dir = "pre_trained_models"
    url_prefix = 'http://download.tensorflow.org/models/'

    if model_name == "mobilenet":
        tar_file = "deeplabv3_mnv2_cityscapes_train_2018_02_05.tar.gz"
    elif model_name == "xception_65":
        tar_file = "deeplabv3_cityscapes_train_2018_02_06.tar.gz"
    elif model_name == "xception_71":
        tar_file = "deeplab_cityscapes_xception71_trainfine_2018_09_08.tar.gz"
    elif model_name == "xception_71_slow":
        tar_file = "deeplab_cityscapes_xception71_trainvalfine_2018_09_08.tar.gz"
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
    """ Class to load DeepLab model and run inference. """

    INPUT_TENSOR_NAME = 'ImageTensor:0'
    OUTPUT_TENSOR_NAME = 'SemanticPredictions:0'
    INPUT_SIZE = 513
    FROZEN_GRAPH_NAME = 'frozen_inference_graph'

    def __init__(self, model_name="mobilenet"):
        """ Creates and loads pretrained deeplab model. """
        self.graph = tf.Graph()
        self.sess = None
        self.load(model_name)
        self.load_segmentation_scheme()
        self.model_name = model_name

    @property
    def name(self):
        """ Returns an identifier for the model. """
        return "deeplab-" + self.model_name

    def load(self, model_name):
        """ Extract frozen graph from tar archive. """
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
        """ Load the City-scapes segmentation/color scheme. """
        self.label_names = []
        self.label_colors = []

        for label in cs_labels:
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

        width, height = image.size
        resize_ratio = 1.0 * self.INPUT_SIZE / max(width, height)
        target_size = (int(resize_ratio * width), int(resize_ratio * height))
        resized_image = image.convert('RGB').resize(
            target_size, Image.ANTIALIAS)
        batch_seg_map = self.sess.run(
            self.OUTPUT_TENSOR_NAME,
            feed_dict={self.INPUT_TENSOR_NAME: [np.asarray(resized_image)]})
        seg_map = batch_seg_map[0]
        results = {
            'seg_map': seg_map,
            'color_map': self.color_map
        }
        return results


def plot_segmentation(image_fp, seg_map, color_map, show=True,
                      plot_labels=None):
    """Visualizes input image, segmentation map and overlay view."""

    # Resize the image to the segmentation map.
    seg_map = np.array(seg_map)
    seg_size = (seg_map.shape[1], seg_map.shape[0])
    with open(image_fp, "rb") as f:
        jpeg_str = f.read()
    orig_image = Image.open(BytesIO(jpeg_str))
    image = orig_image.resize(seg_size, Image.ANTIALIAS)

    label_names = np.array(color_map[0])
    label_colors = np.array(color_map[1])

    label_to_id = {k: i for i, k in enumerate(label_names)}

    plt.figure(figsize=(15, 5))
    grid_spec = gridspec.GridSpec(1, 4, width_ratios=[6, 6, 6, 1])

    # Plot the resized image.
    plt.subplot(grid_spec[0])
    plt.imshow(image)
    plt.axis('off')
    plt.title('input image')

    # Plot the segmentation map with the right colors.
    plt.subplot(grid_spec[1])
    seg_image = label_colors[seg_map].astype(np.uint8)
    plt.imshow(seg_image)
    plt.axis('off')
    plt.title('segmentation map')

    # Overlay the resized image and the segmentation map.
    plt.subplot(grid_spec[2])
    plt.imshow(image)
    plt.imshow(seg_image, alpha=0.7)
    plt.axis('off')
    plt.title('segmentation overlay')

    # Plot the legend showing the segmentation colors and their meaning.
    if plot_labels is not None:
        unique_labels = []
        new_label_names = []
        for key in sorted(plot_labels.items(), key=operator.itemgetter(1),
                          reverse=True):
            class_name = key[0]
            frac = round(100*plot_labels[class_name], 1)
            if frac > 0:
                unique_labels.append(label_to_id[class_name])
                new_label_names.append(f"{class_name} ({frac}%)")
        label_names = np.array(new_label_names)
        unique_labels = np.array(unique_labels)
    else:
        unique_labels = np.unique(seg_map)
        label_names = label_names[unique_labels]

    ax = plt.subplot(grid_spec[3])
    img_colors = np.reshape(label_colors[unique_labels], (-1, 1, 3))
    plt.imshow(img_colors.astype(np.uint8), interpolation='nearest')
    ax.yaxis.tick_right()
    plt.yticks(range(len(unique_labels)), label_names)
    plt.xticks([], [])
    ax.tick_params(width=0.0)
    plt.grid(False)
    if show:
        plt.show()
