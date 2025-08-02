import os
import subprocess as sp
import sys
import re


def set_py_version(version):

    # Set next version in setup.py
    with open(os.path.join(os.getcwd(), 'setup.py'), 'r') as data:
        setup_file = data.read()

    version_regex = "version=\"\d+\.\d+(\.\d+)?(\.\d+)?(rc\d+)?\""
    rgx = re.compile(version_regex, re.IGNORECASE | re.VERBOSE)
    current_version = rgx.search(setup_file)

    replacement = 'version=\"{}\"'.format(version)

    if current_version.group(0) == replacement:
        print("False")
        sys.exit(0)

    setup_file = setup_file.replace(current_version.group(0), replacement)

    with open(os.path.join(os.getcwd(), 'setup.py'), 'w') as data:
        data.write(setup_file)

    print("True")


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser(description='Sets version in setup.py')
    parser.add_argument('--version', help='Version to update in setup.py')

    p = parser.parse_args()

    set_py_version(p.version)
