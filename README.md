# multipart
A script for processing multipart collections into CSVs

## Installation

        git clone git@github.com:UCLALibrary/multipart.git
        cd multipart
        python -m venv ENV
        source ENV/bin/activate
        pip install -r requirements.txt

## Usage

1. First run the script and give it the collection path as an argument.

        python multiwork.py path/to/collection

2. The script will look for an `inputs.yml` file in the root of the collection. If it doesn't exist, it will write a template file. Open it in your text editor and fill it out. This is where the EZID credentials for ARK minting are added. (Considering changing this to input prompt.)

        vim path/to/collection/inputs.txt

3. Now run the script again. It will use the defaults values from inputs as it generates the CSVs.

        python multiwork.py path/to/collection