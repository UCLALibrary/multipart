import argparse
import csv
import os
import uuid
import yaml


YAML_TEMPLATE = """
Collection Title: 

# Collection and Multipart Defaults
Visibility: 
Genre: 
Repository: 
Date.creation: 
Date.normalized: 
Type.typeOfResource: 
Rights.copyrightStatus: 
Rights.servicesContact: 
Language: 

# Volume Defaults
viewingHint: 
Text direction: 
vol title prefix: 
"""

ALL_HEADERS = [
    "Item ARK",
    "Parent ARK",
    "Object Type",
    "Title",
    "File Name",
]

COLLECTION_HEADERS = [
    "Visibility",
    "Genre",
    "Repository",
    "Date.creation",
    "Date.normalized",
    "Type.typeOfResource",
    "Rights.copyrightStatus",
    "Rights.servicesContact",
    "Language"
]

MULTI_HEADERS = COLLECTION_HEADERS + [
    "IIIF Object Type",
    "viewingHint"
]

VOL_HEADERS = [
    "viewingHint",
    "Text direction"
]

PAGE_HEADERS = [
    "Item Sequence"
]


def check_inputs(path):
    yaml_path = os.path.join(path, "inputs.yml")
    if os.path.exists(yaml_path):
        return True
    print(f"Input file not found. Creating template {yaml_path}.")
    print("Please enter default values in that file and retry.")
    with open(yaml_path, "w") as yaml_file:
        yaml_file.write(YAML_TEMPLATE)
    return False


def get_inputs(path):
    yaml_path = os.path.join(path, "inputs.yml")
    with open(yaml_path, "r") as yaml_file:
        defaults = yaml.load(yaml_file, Loader=yaml.Loader)
        title = defaults.pop("Collection Title")
        vol_prefix = defaults.pop("vol title prefix")
        vol_defaults = {k:defaults.pop(k) for k in VOL_HEADERS}
        return title,defaults,vol_prefix,vol_defaults


def process_level0(root, title, defaults):
    csv_path = os.path.join(root, f"{title}-collection.csv")
    ark = uuid.uuid4()
    data = {
        "Item ARK": ark,
        "Object Type": "Collection",
        "Title": title
    }
    data.update(defaults)
    headers = ALL_HEADERS + COLLECTION_HEADERS
    with open(csv_path, "w") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=headers)
        writer.writeheader()
        writer.writerow(data)
    return ark
    

def process_level1(root, title, collection_ark, defaults):
    dirs = sorted([dir for dir in os.scandir(root) if dir.is_dir()], key=lambda x:x.name)
    csv_path = os.path.join(root, f"{title}-multiworks-festerize.csv")
    headers = ALL_HEADERS + MULTI_HEADERS
    works = []
    with open(csv_path, "w") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=headers)
        writer.writeheader()
        for dir in dirs:
            ark = uuid.uuid4()
            data = {
                "Item ARK": ark,
                "Parent ARK": collection_ark,
                "IIIF Object Type": "Collection",
                "Object Type": "Work",
                "viewingHint": "multi-part",
                "Title": dir.name
            }
            data.update(defaults)
            writer.writerow(data)
            works.append((dir,ark))
    return works
    

def process_level2(root, title, works, vol_pre, vol_def):
    csv_path = os.path.join(root, f"{title}-works.csv")
    headers = ALL_HEADERS + VOL_HEADERS
    volumes = []
    with open(csv_path, "w") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=headers)
        writer.writeheader()
        for work, work_ark in works:
            dirs = sorted([dir for dir in os.scandir(work.path) if dir.is_dir()], key=lambda x:x.name)
            for dir in dirs:
                ark = uuid.uuid4()
                data = {
                    "Item ARK": ark,
                    "Parent ARK": work_ark,
                    "Object Type": "Work",
                    "Title": f"{vol_pre} {dir.name}"
                }
                data.update(vol_def)
                writer.writerow(data)
                volumes.append((dir, ark))
    return volumes


def process_level3(root, title, volumes):
    csv_path = os.path.join(root, f"{title}-pages.csv")
    headers = ALL_HEADERS + PAGE_HEADERS
    with open(csv_path, "w") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=headers)
        writer.writeheader()
        for vol, vol_ark in volumes:
            files = sorted([file.name for file in os.scandir(vol.path) if file.is_file()])
            for seq,file in enumerate(files, start=1):
                ark = uuid.uuid4()
                data = {
                    "Item ARK": ark,
                    "Parent ARK": vol_ark,
                    "Object Type": "Page",
                    "Title": f"{vol.name} {seq}",
                    "File Name": os.path.join(vol.path, file),
                    "Item Sequence": seq
                }
                writer.writerow(data)



def main(root):
    title, defaults, vpre, vdef = get_inputs(root)
    collection_ark = process_level0(root, title, defaults)
    works = process_level1(root, title, collection_ark, defaults)
    volumes = process_level2(root, title, works, vpre, vdef)
    process_level3(root, title, volumes)


if __name__ == "__main__":
    parser  = argparse.ArgumentParser(
        prog='multipart',
        description='Generates CSVs at multiple levels for collections containing multi-part objects'
    )
    parser.add_argument('path', help='the path to the collection')
    args = parser.parse_args()
    if check_inputs(args.path) is True:
        main(args.path)
