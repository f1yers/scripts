import requests
from lxml import objectify, etree

def main(appname, version, group):

    group = group.replace('.', '/')

    url = "https://maven-repo.EXAMPLE.com/repository/snapshots/{0}/{1}/{2}-SNAPSHOT/maven-metadata.xml".format(group, appname, version)
    r = requests.get(url)
    root = objectify.fromstring(r.text.encode('utf-8'))
    ts = root.versioning.snapshot.timestamp.text
    bn = root.versioning.snapshot.buildNumber.text

    print(version + '-' + ts + '-' + bn)


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser(description='Find latest SNAPSHOT version for release')
    parser.add_argument('--appname', help='Application name as it appears in the pom.xml')
    parser.add_argument('--version', help='Release version')
    parser.add_argument('--group', help='Nexus group name', default='com.mbopartners.boss')

    p = parser.parse_args()

    main(p.appname, p.version, p.group)
