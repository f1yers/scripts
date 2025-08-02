import os
import subprocess as sp
import sys
import re
import json
from collections import OrderedDict


def set_node_version(version):

    # Set next version in package.json
    with open(os.path.join(os.getcwd(), 'package.json'), 'r') as package_file:
        data = json.load(package_file, object_pairs_hook=OrderedDict)

    if data['version'] != version:
        data['version'] = version
        print("True")
    else:
        print("False")
        sys.exit(0)

    with open('package.json', 'w') as package_file:
        json.dump(data, package_file, indent=4)


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser(description='Sets version in package.json')
    parser.add_argument('--version', help='Version to update in package.json')

    p = parser.parse_args()

    set_node_version(p.version)
