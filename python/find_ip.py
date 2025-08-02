import boto3
import sys


def find_ip(zone, environment, appname, region, id_only):

    ec2 = boto3.resource('ec2', region_name=region)
    instances = ec2.instances.filter(
        Filters=[
            {'Name': 'instance-state-name', 'Values': ['running']}
        ]
    )

    for i in instances:
        if not i.key_name:
            continue
        if not i.network_interfaces_attribute:
            continue
        if i.key_name == 'aws-east-{0}-{1}'.format(appname, environment):
            if i.placement['AvailabilityZone'] == zone:
                if id_only:
                    print(i.id)
                    sys.exit(0)
                print(i.network_interfaces_attribute[0]['PrivateIpAddress'])


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser(description='Discovers IP addresses with supplied parameters')
    parser.add_argument('--zone', help='Search for servers in a specified availability zone')
    parser.add_argument('--environment', help='Search for servers in specified environment')
    parser.add_argument('--appname', help='Search for servers with specified appname')
    parser.add_argument('--region', help='Search for servers in specified region')
    parser.add_argument('--id_only', nargs='?', const=True, default=False,
                                    help='Only return an instance ID')
    parser.set_defaults(zone=None, environment=None, appname=None, region='us-east-1')
    p = parser.parse_args()

    if not p.zone:
        sys.exit('No zone specified')
    if not p.environment:
        sys.exit('No environment specified')
    if not p.appname:
        sys.exit('No appname specified')

    find_ip(p.zone, p.environment, p.appname, p.region, p.id_only)
