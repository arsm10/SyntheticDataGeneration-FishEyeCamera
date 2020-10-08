#!/usr/bin/env python

import cv2
import multiprocessing
import os
import random
import xml.etree.ElementTree as ET

#import xml.etree

from settings import read_label_data
import settings

# only append new classes, never change order,
# if you want to reused existing labeled data
classes = ["person"]

def add_object_to_tree(tree, name, rect):
    obj = ET.SubElement(tree.getroot(), "object")
    ET.SubElement(obj, "name").text = name
    ET.SubElement(obj, "pose").text = "Unspecified"
    ET.SubElement(obj, "truncated").text = "0"
    ET.SubElement(obj, "difficult").text = "0"
    box = ET.SubElement(obj, "bndbox")
    ET.SubElement(box, "xmin").text = str(rect[0])
    ET.SubElement(box, "ymin").text = str(rect[1])
    ET.SubElement(box, "xmax").text = str(rect[0] + rect[2])
    ET.SubElement(box, "ymax").text = str(rect[1] + rect[3])

def convert(size, box):
    dw = 1./size[0]
    dh = 1./size[1]
    x = box[0] + box[2]/2.0
    y = box[1] + box[3]/2.0
    w = box[2]
    h = box[3]
    x = x*dw
    w = w*dw
    y = y*dh
    h = h*dh
    return (x,y,w,h)

def analyze_image(filename):
    global data
    # detect object location
    image_location = os.path.join(settings.image_dir_tmp, filename + ".png")
    image = cv2.imread(image_location)
    if image is None:
        print(image_location, "does not exit. Skip it.")
        return

    result = []

    for datum in data:
        label = datum['label']
        # from RGBA to BGR
        color = tuple(datum['color'][2::-1])

        image_binary = cv2.inRange(image, color, color)
        contours = cv2.findContours(image_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if not contours:
            continue

        for contour in contours[1]:
            rect = cv2.boundingRect(contour)
            # ignore small detections
            if rect[2] < 5 and rect[3] < 5:
                continue
            result.append((label, rect))

    height, width = image.shape[:2]
    return width, height, result

def write_results_voc(filename, width, height, result):
    tree = ET.parse(templatePath)
    for (l, r) in result:
        add_object_to_tree(tree, l, r)

    w = tree.find("size/width")
    w.text = str(width)
    h = tree.find("size/height")
    h.text = str(height)

    tree.write(os.path.join(settings.annotation_dir, filename + ".xml"))

def write_results_yolo(filename, width, height, result):
    with open(os.path.join(settings.labels_dir, filename + ".txt"), 'w') as f:
        for (l, rect) in result:
            bb = convert((width, height), rect)
            if l not in classes:
                continue
            cls_id = classes.index(l)
            f.write(str(cls_id) + " " + " ".join([str(a) for a in bb]) + "\n")

def create_annotation(filename):
    width, height, result = analyze_image(filename)

    write_results_voc(filename, width, height, result)
    write_results_yolo(filename, width, height, result)


# script directory
directory = os.path.dirname(os.path.abspath(__file__))
templatePath = os.path.join(directory, 'template.xml')

# read label-color-mapping file
data = read_label_data(settings.label_map)

files = [f.rstrip(".jpg") for f in os.listdir(settings.image_dir) if os.path.isfile(os.path.join(settings.image_dir, f))]

# create Annotation files
pool = multiprocessing.Pool(4)
pool.map(create_annotation, files)

random.seed(648)

# create ImageSet files
random.shuffle(files)
subset_size = len(files)//2
with open(os.path.join(settings.image_sets_dir, "trainval.txt"), 'w') as f:
    f.write("\n".join(files[:subset_size]))

with open(os.path.join(settings.image_sets_dir, "test.txt"), 'w') as f:
    f.write("\n".join(files[subset_size:]))
