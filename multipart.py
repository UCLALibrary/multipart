import argparse
import csv
import os
import yaml
from getpass import getpass
import requests

YAML_TEMPLATE = """
Collection Title:
Collection ARK:

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
page title prefix:
EZID Username:
EZID Password:
ARK Shoulder:
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

# Function to mint an ARK using the ERC profile
def mint_ark(username, password, shoulder):
    url = f'https://ezid.cdlib.org/shoulder/{shoulder}'  # URL for minting
    headers = {
        'Content-Type': 'text/plain; charset=UTF-8',
    }
    data = {
        '_profile': 'erc',
    }

    # Encode data as UTF-8
    data_encoded = '\n'.join(f'{k}: {v}' for k, v in data.items()).encode('utf-8')
    
    print(f"Request URL: {url}")
    print(f"Request Headers: {headers}")
    print(f"Request Data: {data}")

    response = requests.post(url, headers=headers, data=data_encoded, auth=(username, password))
    
    if response.status_code == 201:
        # ARK successfully minted, return the full ARK identifier
        ark = response.text.strip()
        # Remove 'success: ' if it's part of the response
        if ark.startswith("success: "):
            return ark[len("success: "):].strip()
        return ark
    else:
        # Log error details for debugging
        print(f"Error minting ARK: {response.status_code} - {response.text}")
        print(f"Data sent: {data}")
        return None

def check_inputs(path):
    yaml_path = os.path.join(path, "inputs.yml")
    if os.path.exists(yaml_path):
        return True
    print(f"Input file not found. Creating template {yaml_path}.")
    with open(yaml_path, "w") as yaml_file:
        yaml_file.write(YAML_TEMPLATE)
    return False


def get_inputs(path):
    yaml_path = os.path.join(path, "inputs.yml")
    with open(yaml_path, "r") as yaml_file:
        defaults = yaml.load(yaml_file, Loader=yaml.Loader)
        title = defaults.pop("Collection Title")
        collection_ark = defaults.pop("Collection ARK")
        vol_prefix = defaults.pop("vol title prefix")
        page_prefix = defaults.pop("page title prefix")
        vol_defaults = {k:defaults.pop(k) for k in VOL_HEADERS}
        ezid_user = defaults.pop("EZID Username")
        ezid_password = defaults.pop("EZID Password")
        ark_shoulder = defaults.pop("ARK Shoulder")
        return title,collection_ark,defaults,vol_prefix, page_prefix, vol_defaults, ezid_user, ezid_password, ark_shoulder


def process_level0(root, title, ark, defaults, ezid_user, ezid_password, ark_shoulder):
    csv_path = os.path.join(root, f"{title}-collection.csv")
    if not ark:
        ark = mint_ark(ezid_user, ezid_password, ark_shoulder) #using mint_ark here
        if not ark:
            ark = "ERROR: ARK not minted"
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
    

def process_level1(root, title, collection_ark, defaults, ezid_user, ezid_password, ark_shoulder):
    dirs = sorted([dir for dir in os.scandir(root) if dir.is_dir()], key=lambda x:x.name)
    csv_path = os.path.join(root, f"{title}-multiworks.csv") # Removed "-festerize"
    headers = ALL_HEADERS + MULTI_HEADERS
    works = []
    with open(csv_path, "w") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=headers)
        writer.writeheader()
        for dir in dirs:
            ark = mint_ark(ezid_user, ezid_password, ark_shoulder) #using mint_ark here
            if not ark:
                ark = "ERROR: ARK not minted"
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
    

def process_level2(root, title, works, vol_pre, vol_def, ezid_user, ezid_password, ark_shoulder):
    csv_path = os.path.join(root, f"{title}-vols.csv") # Changed "works" to "vols"
    headers = ALL_HEADERS + VOL_HEADERS
    volumes = []
    with open(csv_path, "w") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=headers)
        writer.writeheader()
        for work, work_ark in works:
            dirs = sorted([dir for dir in os.scandir(work.path) if dir.is_dir()], key=lambda x:x.name)
            for dir in dirs:
                ark = mint_ark(ezid_user, ezid_password, ark_shoulder) #using mint_ark here
                if not ark:
                    ark = "ERROR: ARK not minted"
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


def process_level3(root, title, volumes, page_prefix, ezid_user, ezid_password, ark_shoulder):
    csv_path = os.path.join(root, f"{title}-pages.csv")
    headers = ALL_HEADERS + PAGE_HEADERS
    with open(csv_path, "w") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=headers)
        writer.writeheader()
        for vol, vol_ark in volumes:
            files = sorted([file.name for file in os.scandir(vol.path) if file.is_file()])
            for seq, file in enumerate(files, start=1):
                file_name_without_extension, _ = os.path.splitext(file)  # Remove extension
                what = f"{page_prefix} {file_name_without_extension}"  # Using page_prefix and file name without extension
                ark = mint_ark(ezid_user, ezid_password, ark_shoulder)
                if not ark:
                    ark = "ERROR: ARK not minted"
                data = {
                    "Item ARK": ark,
                    "Parent ARK": vol_ark,
                    "Object Type": "Page",
                    "Title": f"{page_prefix} {file_name_without_extension}",  # Using page_prefix and file name without extension
                    "File Name": os.path.join(vol.path, file),
                    "Item Sequence": seq
                }
                writer.writerow(data)


def main(root):
    title, collection_ark, defaults, vpre, page_prefix, vdef, ezid_user, ezid_password, ark_shoulder = get_inputs(root)
    collection_ark = process_level0(root, title, collection_ark, defaults, ezid_user, ezid_password, ark_shoulder)
    works = process_level1(root, title, collection_ark, defaults, ezid_user, ezid_password, ark_shoulder)
    volumes = process_level2(root, title, works, vpre, vdef, ezid_user, ezid_password, ark_shoulder)
    process_level3(root, title, volumes, page_prefix, ezid_user, ezid_password, ark_shoulder)


if __name__ == "__main__":
    parser  = argparse.ArgumentParser(
        prog='multipart',
        description='Generates CSVs at multiple levels for collections containing multi-part objects'
    )
    parser.add_argument('path', help='the path to the collection')
    args = parser.parse_args()
    if check_inputs(args.path) is True:
        main(args.path)

