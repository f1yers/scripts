from distutils.version import LooseVersion
import subprocess as sp
import json
import sys
import os
import boto3
import shutil


def get_version(appname, branch_type):

    s3 = boto3.resource('s3')
    bucket = s3.Bucket('ci-metadata')
    bucket_prefix = "{0}/{1}".format(appname, branch_type)
    objs = bucket.objects.filter(Prefix=bucket_prefix)
    obj_list = []
    for obj in objs:
        if obj.key.split('/')[2]:
            file_name = obj.key.split('/')[2]
            obj_list.append(os.path.splitext(file_name)[0])

    obj_list.sort(key=LooseVersion)
    version = obj_list.pop()

    return version


def update_rerun_count(appname, version, branch_type):

    if not version:
        version = get_version(appname, branch_type)
    file_name = "{}.json".format(version)
    tmp_version_dir = '/tmp/{}'.format(appname)
    if not os.path.exists(tmp_version_dir):
        os.makedirs(tmp_version_dir)

    fs_file_location = os.path.join(tmp_version_dir, file_name)
    s3_file_location = os.path.join(appname, branch_type, file_name)
    s3 = boto3.resource('s3')
    bucket = s3.Bucket('ci-metadata')
    bucket.download_file(s3_file_location, fs_file_location)

    with open(fs_file_location) as data_file:
        data = json.load(data_file)
        rerun = data['rerun']
        if not rerun:
            data['rerun'].append(1)
            with open(fs_file_location, 'w') as data_file:
                json.dump(data, data_file)
        else:
            max_version = max(rerun)
            new_version = max_version+1
            data['rerun'].append(new_version)
            with open(fs_file_location, 'w') as data_file:
                json.dump(data, data_file)

        s3c = boto3.client('s3')
        s3c.upload_file(fs_file_location, 'ci-metadata', s3_file_location)
        clean_up_tmp(appname)


def clean_up_tmp(appname):

    tmp_version_dir = '/tmp/{}'.format(appname)
    if os.path.exists(tmp_version_dir):
        shutil.rmtree(tmp_version_dir)


def find_metadata(appname, version, discover,
                  hide_rerun_count, rc_versions,
                  branch_type):

    if not version:
        version = get_version(appname, branch_type)
    s3 = boto3.resource('s3')
    bucket = s3.Bucket('ci-metadata')
    file_name = "{}.json".format(version)
    tmp_version_dir = '/tmp/{}'.format(appname)
    if not os.path.exists(tmp_version_dir):
        os.makedirs(tmp_version_dir)

    fs_file_location = os.path.join(tmp_version_dir, file_name)
    s3_file_location = os.path.join(appname, branch_type, file_name)
    bucket.download_file(s3_file_location, fs_file_location)

    with open(fs_file_location) as data_file:
        data = json.load(data_file)
        rerun = data['rerun']
        ticket = data['ticket']
        version_id = data['fixId']

        if discover == 'ticket':
            print(ticket)
        if discover == 'version_id':
            print(version_id)
        if discover == 'rerun_count':
            print(rerun)
        if discover == 'version':
            if hide_rerun_count:
                print(version)
            else:
                if rerun:
                    max_rerun = max(rerun)
                    if max_rerun == 0:
                        print(version)
                    elif rc_versions:
                        print("{0}rc{1}".format(str(version), str(max_rerun)))
                    else:
                        print("{0}-{1}".format(str(version), str(max_rerun)))
                else:
                    print(version)

    clean_up_tmp(appname)


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser(description='Prints metadata about a given version')
    parser.add_argument('--appname', help='Application name (required)')
    parser.add_argument('--branch_type', help='Specify if version is a release or hotfix')
    parser.add_argument('--version', help='Application version to pull metadata from (optional)')
    parser.add_argument('--discover', help='Calls the find_metadata function to discover info about a version')
    parser.add_argument('--update_rerun_count', nargs='?', const=True, default=False,
                        help='Updates rerun count in metadata')
    parser.add_argument('--hide_rerun_count', nargs='?', const=True, default=False,
                        help='Removes rerun count when returning a version')
    parser.add_argument('--rc_versions', nargs='?', const=True, default=False,
                        help='Returns rerun count using rc separator')

    p = parser.parse_args()

    if not p.branch_type:
        p.branch_type = 'release'

    if p.version:
        if "-" in p.version:
            p.version = p.version.split("-")[0]
        if "rc" in p.version:
            p.version = p.version.split("rc")[0]

    if p.discover:
        find_metadata(p.appname, p.version,
                      p.discover, p.hide_rerun_count,
                      p.rc_versions, p.branch_type)
    if p.update_rerun_count:
        update_rerun_count(p.appname, p.version,
                           p.branch_type)
