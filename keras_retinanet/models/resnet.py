"""
Copyright 2017-2018 Fizyr (https://fizyr.com)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import keras
from keras.utils import get_file
import keras_resnet
import keras_resnet.models

from . import retinanet
from . import Backbone
from ..utils.image import preprocess_image

import copy

class ResNetBackbone(Backbone):
    """ Describes backbone information and provides utility functions.
    """

    def __init__(self, backbone):
        super(ResNetBackbone, self).__init__(backbone)
        self.custom_objects.update(keras_resnet.custom_objects)

    def retinanet(self, *args, **kwargs):
        """ Returns a retinanet model using the correct backbone.
        """
        return resnet_retinanet(*args, backbone=self.backbone, **kwargs)

    def dualstream_retinanet(self, *args, **kwargs):
        """ Returns a retinanet model using the correct backbone.
        """
        return dualresnet_retinanet(*args, backbone=self.backbone, **kwargs)

    def download_imagenet(self):
        """ Downloads ImageNet weights and returns path to weights file.
        """
        print("Downloading ImageNet weights for ResNet...")
        resnet_filename = 'ResNet-{}-model.keras.h5'
        resnet_resource = 'https://github.com/fizyr/keras-models/releases/download/v0.0.1/{}'.format(resnet_filename)
        depth = int(self.backbone.replace('resnet', ''))

        filename = resnet_filename.format(depth)
        resource = resnet_resource.format(depth)
        if depth == 50:
            checksum = '3e9f4e4f77bbe2c9bec13b53ee1c2319'
        elif depth == 101:
            checksum = '05dc86924389e5b401a9ea0348a3213c'
        elif depth == 152:
            checksum = '6ee11ef2b135592f8031058820bb9e71'

        return get_file(
            filename,
            resource,
            cache_subdir='models',
            md5_hash=checksum
        )

    def validate(self):
        """ Checks whether the backbone string is correct.
        """
        allowed_backbones = ['resnet50', 'resnet101', 'resnet152']
        backbone = self.backbone.split('_')[0]

        if backbone not in allowed_backbones:
            raise ValueError('Backbone (\'{}\') not in allowed backbones ({}).'.format(backbone, allowed_backbones))

    def preprocess_image(self, inputs):
        """ Takes as input an image and prepares it for being passed through the network.
        """
        return preprocess_image(inputs, mode='caffe')


def resnet_retinanet(num_classes, backbone='resnet50', input_depth=3, modifier=None,  weights=None, skip_mismatch=True, **kwargs):
    """ Constructs a retinanet model using a resnet backbone.

    Args
        num_classes: Number of classes to predict.
        backbone: Which backbone to use (one of ('resnet50', 'resnet101', 'resnet152')).
        inputs: The inputs to the network (defaults to a Tensor of shape (None, None, 3)).
        modifier: A function handler which can modify the backbone before using it in retinanet (this can be used to freeze backbone layers for example).

    Returns
        RetinaNet model with a ResNet backbone.
    """
    # choose default input
    if keras.backend.image_data_format() == 'channels_first':
        inputs = keras.layers.Input(shape=(input_depth, None, None))
    else:
        inputs = keras.layers.Input(shape=(None, None, input_depth))

    # create the resnet backbone
    if backbone == 'resnet50':
        resnet = keras_resnet.models.ResNet50(inputs, include_top=False, freeze_bn=True)
    elif backbone == 'resnet101':
        resnet = keras_resnet.models.ResNet101(inputs, include_top=False, freeze_bn=True)
    elif backbone == 'resnet152':
        resnet = keras_resnet.models.ResNet152(inputs, include_top=False, freeze_bn=True)
    else:
        raise ValueError('Backbone (\'{}\') is invalid.'.format(backbone))

    # invoke modifier if given
    if modifier:
        resnet = modifier(resnet)

    if weights is not None:
        print("Loading weights")
        resnet.load_weights(weights, by_name=True, skip_mismatch=skip_mismatch)

    # create the full model
    return retinanet.retinanet(inputs=inputs, num_classes=num_classes, backbone_layers=resnet.outputs[1:], **kwargs)

def dualresnet_retinanet(num_classes, backbone='resnet50', input_depth_a=3, input_depth_b=3, modifier=None,  weights=None, skip_mismatch=True, **kwargs):
    """ Constructs a retinanet model using a resnet backbone.

    Args
        num_classes: Number of classes to predict.
        backbone: Which backbone to use (one of ('resnet50', 'resnet101', 'resnet152')).
        inputs: The inputs to the network (defaults to a Tensor of shape (None, None, 3)).
        modifier: A function handler which can modify the backbone before using it in retinanet (this can be used to freeze backbone layers for example).

    Returns
        RetinaNet model with a ResNet backbone.
    """
    # choose default input
    if keras.backend.image_data_format() == 'channels_first':
        inputs_a = keras.layers.Input(shape=(input_depth_a, None, None))
        inputs_b = keras.layers.Input(shape=(input_depth_b, None, None))
    else:
        inputs_a = keras.layers.Input(shape=(None, None, input_depth_a))
        inputs_b = keras.layers.Input(shape=(None, None, input_depth_b))

    # create the resnet backbone
    if backbone == 'resnet50':
        resnet_a = keras_resnet.models.ResNet50(inputs_a, include_top=False, freeze_bn=True)
        resnet_b = keras_resnet.models.ResNet50(inputs_b, include_top=False, freeze_bn=True)
    elif backbone == 'resnet101':
        resnet_a = keras_resnet.models.ResNet101(inputs_a, include_top=False, freeze_bn=True)
        resnet_b = keras_resnet.models.ResNet101(inputs_b, include_top=False, freeze_bn=True)
    elif backbone == 'resnet152':
        resnet_a = keras_resnet.models.ResNet152(inputs_a, include_top=False, freeze_bn=True)
        resnet_b = keras_resnet.models.ResNet152(inputs_b, include_top=False, freeze_bn=True)
    else:
        raise ValueError('Backbone (\'{}\') is invalid.'.format(backbone))

    # invoke modifier if given
    if modifier:
        resnet_a = modifier(resnet_a)
        resnet_b = modifier(resnet_b)

    # load pre-trained weights if defined
    if weights is not None:
        print("Loading weights")
        resnet_a.load_weights(weights, by_name=True, skip_mismatch=skip_mismatch)
        resnet_b.load_weights(weights, by_name=True, skip_mismatch=skip_mismatch)

    # rename layer name of each resnet stream
    for layer in resnet_a.layers:
        layer.name = layer.name + "_a"
    for layer in resnet_b.layers:
        layer.name = layer.name + "_b"

    # create the full model
    return retinanet.dualstream_retinanet(inputs_a=inputs_a, inputs_b=inputs_b, 
                                        num_classes=num_classes, 
                                        backbone_layers_a=resnet_a.outputs[1:], 
                                        backbone_layers_b=resnet_b.outputs[1:], 
                                        **kwargs)

def resnet50_retinanet(num_classes, inputs=None, **kwargs):
    return resnet_retinanet(num_classes=num_classes, backbone='resnet50', inputs=inputs, **kwargs)

def resnet101_retinanet(num_classes, inputs=None, **kwargs):
    return resnet_retinanet(num_classes=num_classes, backbone='resnet101', inputs=inputs, **kwargs)

def resnet152_retinanet(num_classes, inputs=None, **kwargs):
    return resnet_retinanet(num_classes=num_classes, backbone='resnet152', inputs=inputs, **kwargs)
