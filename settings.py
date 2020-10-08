import json
import os
from datetime import datetime

if __name__ == "__main__":
    print("You cannot run this file directly.")
    exit()

# user defined values
date = datetime.now().strftime("%Y%m%d_%H%M")
date = ""
target_dir = os.path.join("C:/Users/Muhammad Arshan/Desktop/TU Chemnitz/ICS/Research Project/Research Related Documents", "results", "synthetic", date)

label_map = os.path.join(target_dir, "label_map.json")

def create_dir(root_path, *subdirs):
    directory = os.path.join(root_path, *subdirs)
    # create target directories if not exist
    os.makedirs(directory, exist_ok=True)
    return directory

def read_label_data(file_path):
    with open(file_path, "r") as f:
        return json.load(f)

def write_label_data(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f)

image_dir = create_dir(target_dir, "JPEGImages")
image_dir_tmp = create_dir(target_dir, "JPEGImages_tmp")
annotation_dir = create_dir(target_dir, "Annotations")
labels_dir = create_dir(target_dir, "labels")
image_sets_dir = create_dir(target_dir, "ImageSets", "Main")

