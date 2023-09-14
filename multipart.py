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


def build_row_dict(headers, data):
    row_dict = {key:"" for key in headers}
    for key,value in data.items():
        row_dict[key] = value
    return row_dict


def proc_lvl2(path, title, work_ark, vol_pre, vol_def):
    dirs = [dir for dir in os.scandir(path) if dir.is_dir()]
    print(f"dirs={dirs}")
    csv_path = os.path.join(path, f"{title}-multiworks-festerize.csv")
    headers = ALL_HEADERS + VOL_HEADERS
    with open(csv_path, "w") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=headers)
        writer.writeheader()
        data = {
            "Item ARK": uuid.uuid4(),
            "Parent ARK": work_ark,
            "Object Type": "Work",
            "Title": f"{vol_pre} {dir.name}"
        }
        data.update(vol_def)
        writer.writerow(data)


def proc_lvls0and1(path, title, defaults, vol_pre, vol_def):
    # part 1: collection csv
    csv_path = os.path.join(path, f"{title}-collection.csv")
    collection_ark = uuid.uuid4() # TODO: replace uuid with real ARK
    data = {
        "Item ARK": collection_ark,
        "Object Type": "Collection",
        "Title": title
    }
    data.update(defaults)
    headers = ALL_HEADERS + COLLECTION_HEADERS
    with open(csv_path, "w") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=headers)
        writer.writeheader()
        writer.writerow(data)
    
    # part 2: works csv
    dirs = [dir for dir in os.scandir(path) if dir.is_dir()]
    print(f"dirs={dirs}")
    csv_path = os.path.join(path, f"{title}-multiworks-festerize.csv")
    headers = ALL_HEADERS + MULTI_HEADERS
    with open(csv_path, "w") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=headers)
        writer.writeheader()
        for dir in dirs:
            data = {
                "Item ARK": uuid.uuid4(),
                "Parent ARK": collection_ark,
                "IIIF Object Type": "Collection",
                "Object Type": "Work",
                "viewingHint": "multi-part",
                "Title": dir.name
            }
            data.update(defaults)
            writer.writerow(data)
    for dir in dirs:
        print(f"dir path: {dir.path}")
        #process level 1
        pass
    


def main():
    parser  = argparse.ArgumentParser(
        prog='multipart',
        description='Generates CSVs at multiple levels for collections containing multi-part objects'
    )
    parser.add_argument('path', help='the path to the collection')
    args = parser.parse_args()
    if check_inputs(args.path) is True:
        coll_title,defaults,vol_prefix,vol_defaults = get_inputs(args.path)
        proc_lvl0(args.path, coll_title, defaults, vol_prefix, vol_defaults)


if __name__ == "__main__":
    main()
