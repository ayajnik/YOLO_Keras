# -*- coding: utf-8 -*-
"""YOLO.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1nKUYzMd2N7xpdiMMcCzfw5NeBVOoTXV8
"""

!pip install tensorflow

!pip install --upgrade git+https://github.com/keras-team/keras-cv -q

import os
from tqdm.auto import tqdm
import xml.etree.ElementTree as ET

import tensorflow as tf
from tensorflow import keras

import keras_cv
from keras_cv import bounding_box
from keras_cv import visualization

! curl -L "https://public.roboflow.com/ds/zEDe9ImuHb?key=BWnWVluozH" > roboflow.zip; unzip roboflow.zip; rm roboflow.zip

os.getcwd()

os.chdir('/content/export/')

os.getcwd()

os.mkdir('annotations')

os.mkdir('images')

SPLIT_RATIO = 0.2
BATCH_SIZE = 4
LEARNING_RATE = 0.001
EPOCH = 5
GLOBAL_CLIPNORM = 10.0

import shutil
files = os.listdir()

for file in files:
    # If the file is a .jpg file
    if file.endswith('.jpg'):
        # Copy it into the 'images' directory
        shutil.copy(file, 'images')

import glob
# Get a list of all .jpg files in the current directory
files = glob.glob('*.jpg')

# For each file in the list
for file in files:
    # Delete the file
    os.remove(file)

files = os.listdir()

for file in files:
    # If the file is a .jpg file
    if file.endswith('.xml'):
        # Copy it into the 'images' directory
        shutil.copy(file, 'annotations')

# Get a list of all .jpg files in the current directory
files = glob.glob('*.xml')

# For each file in the list
for file in files:
    # Delete the file
    os.remove(file)

class_ids = [
    'car', 'pedestrian', 'biker', 'truck', 'trafficLight-Red',
        'trafficLight', 'trafficLight-Green', 'trafficLight-RedLeft',
        'trafficLight-GreenLeft', 'trafficLight-Yellow',
        'trafficLight-YellowLeft'
]
class_mapping = dict(zip(range(len(class_ids)), class_ids))
print(class_mapping)

# Path to images and annotations
path_images = "/content/export/images/"
path_annot = "/content/export/annotations/"

# Get all XML file paths in path_annot and sort them
xml_files = sorted(
    [
        os.path.join(path_annot, file_name)
        for file_name in os.listdir(path_annot)
        if file_name.endswith(".xml")
    ]
)
print(xml_files[0:2])
print('\n')
# Get all JPEG image file paths in path_images and sort them
jpg_files = sorted(
    [
        os.path.join(path_images, file_name)
        for file_name in os.listdir(path_images)
        if file_name.endswith(".jpg")
    ]
)
print(jpg_files[0:2])

import xml.etree.ElementTree as ET
tree = ET.parse('/content/export/annotations/1478019952686311006_jpg.rf.69b66a4136dffdf28f07a91f5649bb98.xml')

root=tree.getroot()
image_name = root.find("filename").text

classes = []

for obj in root.iter("object"):
    cls = obj.find("name").text
    classes.append(cls)

classes

def parse_annotation(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    image_name = root.find("filename").text
    image_path = os.path.join(path_images, image_name)

    boxes = []
    classes = []
    for obj in root.iter("object"):
        cls = obj.find("name").text
        classes.append(cls)

        bbox = obj.find("bndbox")
        xmin = float(bbox.find("xmin").text)
        ymin = float(bbox.find("ymin").text)
        xmax = float(bbox.find("xmax").text)
        ymax = float(bbox.find("ymax").text)
        boxes.append([xmin, ymin, xmax, ymax])

    class_ids = [
        list(class_mapping.keys())[list(class_mapping.values()).index(cls)]
        for cls in classes
    ]
    return image_path, boxes, class_ids

image_paths = []
bbox = []
classes = []
for xml_file in tqdm(xml_files):
    image_path, boxes, class_ids = parse_annotation(xml_file)
    image_paths.append(image_path)
    bbox.append(boxes)
    classes.append(class_ids)

bbox = tf.ragged.constant(bbox)
classes = tf.ragged.constant(classes)
image_paths = tf.ragged.constant(image_paths)

data = tf.data.Dataset.from_tensor_slices((image_paths, classes, bbox))

bbox

classes

image_paths

for i in data:
    print(i)

# Determine the number of validation samples
num_val = int(len(xml_files) * SPLIT_RATIO)

# Split the dataset into train and validation sets
val_data = data.take(num_val)
train_data = data.skip(num_val)

num_val

val_data

def load_image(image_path):
    image = tf.io.read_file(image_path)
    image = tf.image.decode_jpeg(image, channels=3)
    return image


def load_dataset(image_path, classes, bbox):
    # Read Image
    image = load_image(image_path)
    bounding_boxes = {
        "classes": tf.cast(classes, dtype=tf.float32),
        "boxes": bbox,
    }
    return {"images": tf.cast(image, tf.float32), "bounding_boxes": bounding_boxes}

augmenter = keras.Sequential(
    layers=[
        keras_cv.layers.RandomFlip(mode="horizontal", bounding_box_format="xyxy"),
        keras_cv.layers.RandomShear(
            x_factor=0.2, y_factor=0.2, bounding_box_format="xyxy"
        ),
        keras_cv.layers.JitteredResize(
            target_size=(640, 640), scale_factor=(0.75, 1.3), bounding_box_format="xyxy"
        ),
    ]
)

train_ds = train_data.map(load_dataset, num_parallel_calls=tf.data.AUTOTUNE)

train_ds = train_ds.shuffle(BATCH_SIZE * 4)
train_ds = train_ds.ragged_batch(BATCH_SIZE, drop_remainder=True)
train_ds = train_ds.map(augmenter, num_parallel_calls=tf.data.AUTOTUNE)

"""In the above code we have used some new methods that are available in Tensorflow.



1.   tf.ragged.constant: Ragged tensors are TensorFlow's way of representing lists of lists with varying lengths. They are used here because the number of bounding boxes and classes can vary for each image.

2.   tf.data.Dataset: A tf.data.Dataset represents a sequence of elements, where each element consists of one or more components. In this case, each element of the dataset is a tuple containing an image path, classes, and bounding boxes. The tf.data.Dataset.from_tensor_slices function is used to create the dataset. This function takes as input one (or multiple) tensors and returns a dataset. Each element in the returned dataset is a slice from the first dimension of the input tensor(s)

3. The tf.data.Dataset.map() method is used to apply a function to each element of a dataset. The syntax is:
    
    
    dataset.map(function, num_parallel_calls=None)

    a. function here is the object to which we want to apply transformation.
    b. num_parallel_calls is an optional argument which tells tensorflow to execute
    commands parallely. There is a default option called ** tf.data.Autotune ** . This
    automatically allocates CPU threads based on infrastructure.


"""

resizing = keras_cv.layers.JitteredResize(
    target_size=(640, 640),
    scale_factor=(0.75, 1.3),
    bounding_box_format="xyxy",
)

val_ds = val_data.map(load_dataset, num_parallel_calls=tf.data.AUTOTUNE)
val_ds = val_ds.shuffle(BATCH_SIZE * 4)
val_ds = val_ds.ragged_batch(BATCH_SIZE, drop_remainder=True)
val_ds = val_ds.map(resizing, num_parallel_calls=tf.data.AUTOTUNE)

"""In the above preparation of the data, we see that for training data, we are augmenting the data while we are resizing the data. There is a specific reason for this.

The primary reason for not using data augmentation in the validation set is to keep the validation data as close as possible to the real-world data on which the model will be eventually tested. Data augmentation is a technique used to artificially increase the size of the training dataset by creating modified versions of the images in the dataset. This can include operations such as rotations, translations, zooming, flipping, etc.

While data augmentation is beneficial for improving the model's ability to generalize from the training data, it is not typically used on validation or test data. This is because augmentation can distort the data, and you want your validation set to reflect the real-world data your model will be encountering as closely as possible learnopencv.com, towardsdatascience.com.

In your specific code snippet, you're using keras_cv.layers.JitteredResize to resize the images in the validation set. Resizing is a necessary pre-processing step because the model expects input images of a specific size. The JitteredResize function not only resizes the images but also adds a bit of random scaling (between 0.75 and 1.3 in your case) to introduce some amount of randomness in the validation data, which can help to make the validation process more robust. However, this is not considered data augmentation because it does not create additional data and is a necessary step for the model to process the images learnopencv.com, docs.ultralytics.com.

In summary, the primary goal of data augmentation is to increase the diversity of the training data and reduce overfitting. In contrast, the goal of the validation process is to estimate how well the model has learned to generalize from the training data to unseen data. Therefore, it's common practice to apply data augmentation to the training data and not to the validation data.
"""

def visualize_dataset(inputs, value_range, rows, cols, bounding_box_format):
    inputs = next(iter(inputs.take(1)))
    images, bounding_boxes = inputs["images"], inputs["bounding_boxes"]
    visualization.plot_bounding_box_gallery(
        images,
        value_range=value_range,
        rows=rows,
        cols=cols,
        y_true=bounding_boxes,
        scale=5,
        font_scale=0.7,
        bounding_box_format=bounding_box_format,
        class_mapping=class_mapping,
    )


visualize_dataset(
    train_ds, bounding_box_format="xyxy", value_range=(0, 255), rows=2, cols=2
)

visualize_dataset(
    val_ds, bounding_box_format="xyxy", value_range=(0, 255), rows=2, cols=2
)

def dict_to_tuple(inputs):
    return inputs["images"], inputs["bounding_boxes"]


train_ds = train_ds.map(dict_to_tuple, num_parallel_calls=tf.data.AUTOTUNE)
train_ds = train_ds.prefetch(tf.data.AUTOTUNE)

val_ds = val_ds.map(dict_to_tuple, num_parallel_calls=tf.data.AUTOTUNE)
val_ds = val_ds.prefetch(tf.data.AUTOTUNE)

for i in train_ds:
    print(i)

backbone = keras_cv.models.YOLOV8Backbone.from_preset(
    "yolo_v8_s_backbone_coco"  # We will use yolov8 small backbone with coco weights
)

yolo = keras_cv.models.YOLOV8Detector(
    num_classes=len(class_mapping),
    bounding_box_format="xyxy",
    backbone=backbone,
    fpn_depth=1,
)

optimizer = tf.keras.optimizers.Adam(
    learning_rate=LEARNING_RATE,
    global_clipnorm=GLOBAL_CLIPNORM,
)

yolo.compile(
    optimizer=optimizer, classification_loss="binary_crossentropy", box_loss="ciou"
)

class EvaluateCOCOMetricsCallback(keras.callbacks.Callback):
    def __init__(self, data, save_path):
        super().__init__()
        self.data = data
        self.metrics = keras_cv.metrics.BoxCOCOMetrics(
            bounding_box_format="xyxy",
            evaluate_freq=1e9,
        )

        self.save_path = save_path
        self.best_map = -1.0

    def on_epoch_end(self, epoch, logs):
        self.metrics.reset_state()
        for batch in self.data:
            images, y_true = batch[0], batch[1]
            y_pred = self.model.predict(images, verbose=0)
            self.metrics.update_state(y_true, y_pred)

        metrics = self.metrics.result(force=True)
        logs.update(metrics)

        current_map = metrics["MaP"]
        if current_map > self.best_map:
            self.best_map = current_map
            self.model.save(self.save_path)  # Save the model when mAP improves

        return logs

"""
## Train the Model
"""

yolo.fit(
    train_ds,
    validation_data=val_ds,
    epochs=3,
    callbacks=[EvaluateCOCOMetricsCallback(val_ds, "model.h5")],
)

! pip freeze > requirements.txt

