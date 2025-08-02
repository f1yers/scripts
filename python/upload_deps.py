import requests
import json
from urllib import urlretrieve
import os
import subprocess as sp
import tarfile
import shutil


def main(cookbook, get_deps):

    tmp_path = '/tmp/cookbook_upload'
    if os.path.exists(tmp_path):
        shutil.rmtree(tmp_path)
    if not os.path.exists(tmp_path):
        os.makedirs(tmp_path)

    public_url = 'https://supermarket.chef.io/api/v1/cookbooks/' + cookbook
    headers = {'content-type': 'application/json'}

    print cookbook
    results = requests.get(public_url, headers=headers)
    version_list = json.loads(results.text)
    latest_version = version_list['latest_version']

    if get_deps:
        # Get dep list
        results = requests.get(latest_version, headers=headers)
        dep_version_list = json.loads(results.text)
        if 'dependencies' in dep_version_list:
            dep_list = dep_version_list['dependencies']

            for dep in dep_list:
                print dep
                dep_url = 'https://supermarket.chef.io/api/v1/cookbooks/' + dep
                # Get dep versions
                results = requests.get(dep_url, headers=headers)
                dep_version_list = json.loads(results.text)
                for dep_version_url in dep_version_list['versions']:
                    save_tgz(tmp_path, dep, dep_version_url)

            upload(tmp_path)

    for version_url in version_list['versions']:
        save_tgz(tmp_path, cookbook, version_url)
        upload(tmp_path)


def upload(tmp_path):

    for tgz in os.listdir(tmp_path):
            tgz_path = tmp_path + '/' + tgz
            print tgz_path
            os.chdir(tmp_path)
            tar = tarfile.open(tgz)
            mem_name = tar.getnames()
            share_name = mem_name[0].split('/')[0]
            tar.extractall()
            tar.close()

            proc = sp.Popen(['knife', 'supermarket', 'share',
                           share_name, 'other', '-o', tmp_path])
            proc.communicate()

            os.remove(tgz_path)
            shutil.rmtree(share_name)


def save_tgz(tmp_path, cookbook, version_url):

        print version_url + '/download'
        version = version_url.split('/')
        version = version[8]
        tgz_file_location = "{0}/{1}-{2}.tar.gz".format(tmp_path, cookbook, version)
        if not os.path.exists(tgz_file_location):
            urlretrieve(version_url + '/download', tgz_file_location)
            print "Added {}".format(tgz_file_location)


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser(description='Uploads all cookbook dependencies to private supermarket from public')
    parser.add_argument('--cookbook', help='Enter a valid cookbook name found on the public supermarket')
    parser.add_argument('--get_deps', help='Defaults to true, can be turned off to only get cookbook specified')
    parser.set_defaults(get_deps=True)
    p = parser.parse_args()

    main(p.cookbook, p.get_deps)