import sys
import subprocess as sp
import json
import os
import shlex
import boto3

"""
This script wraps the knife-ec2 command
so we can deploy to multiple az's in parallel with one command
Checks if a keypair exists, if not it will create and save it
Also handles removal of chef node and deletion of ec2 instances

usage: deploy.py [-h] [--appname APPNAME] [--vpc VPC] [--tier TIER]
                            [--env ENV] [--ec2_size EC2_SIZE]
                            [--groups GROUPS] [--zones ZONES]
                            [--iam_profile_id IAM_PROFILE_ID]

Wraps knife-ec2 with additional functionality

optional arguments:
  -h, --help            show this help message and exit
  --appname APPNAME     Application name should be equal to the github repo
                        name
  --vpc VPC             VPC id to create the instance in
  --tier TIER           Tier to deploy instance to (app, public)
  --env ENV             Environment to deploy to (preprod or production)
  --ec2_size EC2_SIZE   Size of EC2 instance (t2.micro, m3.medium, etc)
  --groups GROUPS       Security group ids to apply to the instance
  --zones ZONES         List of availability zones to deploy to (us-east-1a
                        ,us-east-1c,us-east-1e)
  --iam_profile_id IAM_PROFILE_ID
                        Must be supplied if released=True to close fix version

Example:
python3 /opt/repositories/dev-ops/scripts/ci/deploy.py \
--appname=example \
--vpc=vpc-id\
--env=preprod \
--tier=app \
--ec2_size=t2.micro \
--groups=sg-asdfas1,sg-asdfas2,sg-asdfas3,sg-asdfas4 \
--zones=us-east-1a,us-east-1c
"""


def main(appname, vpc, env, tier, ec2_size,
         groups, zones, iam_profile_id,
         chef_client_version, ami_id,
         datadog):

    print("Appname: " + appname)
    print("VPC: " + vpc)
    print("ENV: " + env)
    print("Tier: " + tier)
    print("EC2 Size: " + ec2_size)
    print("SGroups: " + groups)
    print("Zones: " + zones)

    # Load subnets metadata and pull out a dict of subnets
    subnet_json = os.path.join('./', 'subnets.json')
    with open(subnet_json) as data_file:
        subnet_data = json.load(data_file)

    if vpc == 'vpc-1':
        product = 'example1'
        if not ami_id:
            ami_id = 'ami-id'
        if env == 'preprod':
            if tier == 'app':
                subnets = subnet_data['vpc-1']['preprod']['app']
        elif env == 'production':
            if tier == 'app':
                subnets = subnet_data['vpc-1']['production']['app']
    if vpc == 'vpc-2':
        product = 'example2'
        if not ami_id:
            ami_id = 'ami-id'
        if env == 'preprod':
            if tier == 'app':
                subnets = subnet_data['vpc-2']['preprod']['app']
            elif tier == 'public':
                subnets = subnet_data['vpc-2']['preprod']['public']
        elif env == 'production':
            if tier == 'app':
                subnets = subnet_data['vpc-2']['production']['app']
            elif tier == 'public':
                subnets = subnet_data['vpc-2']['production']['public']

    print("Subnets: {}".format(json.dumps(subnets)))
    sys.stdout.flush()
    # Create keypair for specified app name and store in .ssh dir
    create_keypair(appname, env)

    # Discover existing instance id's before creating new ones
    print("Checking for existing instances")
    existing_servers = discover_ids(appname, env)
    kill_list = []
    # We only want to terminate existing server(s) in zones we're deploying to
    for server in existing_servers:
        if server['zone'] in zones:
            kill_list.append(server['instance_id'])

    if len(kill_list) > 0:
        print("REPLACING: {}".format(kill_list))
        sys.stdout.flush()
    # Create ec2 instances and boostrap them with the chef server
    zones = zones.split(",")
    deploy_to = []
    for az, subnet in subnets.items():
        if az in zones:
            deploy_to.append(subnet)

    print("DEPLOYING TO: {}".format(deploy_to))
    sys.stdout.flush()
    knife_cmds = ["knife ec2 server create -r \
    'recipe[environment::{4}],recipe[{0}::default]' -I {8} \
    --subnet {1} -f {2} --security-group-ids {3} -x centos -S aws-east-{0}-{4} \
    -i ~/.ssh/aws-east-{0}-{4}.pem --bootstrap-version {5} --environment {4} \
    -T product={7},appname={0},environment={4},chef_client_version={5},datadog-agent={9} \
    {6}".format(appname, s, ec2_size,
                groups, env, chef_client_version,
                iam_profile_id, product, ami_id,
                datadog) for s in deploy_to]
    split_cmds = []
    for c in knife_cmds:
        split_cmds.append(shlex.split(c))
    processes = [sp.Popen(cmd)
                 for cmd in split_cmds]

    exitcodes = [p.wait() for p in processes]

    print("RETURN CODES FOR EACH PROCESS: {}".format(exitcodes))

    for code in exitcodes:
        if int(code) != 0:
            print("Non-zero exit code returned")
            sys.exit(1)

    # Remove old instances
    if kill_list:
        delete_instances(kill_list)
    else:
        print("No instances to destroy")


def discover_ids(appname, env):

    ec2 = boto3.resource('ec2', region_name='us-east-1')
    instances = ec2.instances.filter(
        Filters=[
            {'Name': 'instance-state-name', 'Values': ['running']}
        ]
    )

    existing_servers = []
    for i in instances:
        if not i.key_name:
            continue
        if not i.network_interfaces_attribute:
            continue
        if i.key_name == 'aws-east-{0}-{1}'.format(appname, env):
            existing_servers.append({
                'instance_id': i.instance_id,
                'private_ip': i.network_interfaces_attribute[0]['PrivateIpAddress'],
                'zone': i.placement['AvailabilityZone'],
                'key_name': i.key_name})

    return existing_servers


def check_keypair(keypair_name):

    keypair_list = sp.check_output(['aws', 'ec2', 'describe-key-pairs',
                                    '--region', 'us-east-1'])
    keypair_list = keypair_list.decode('UTF-8')
    keypair_list = json.loads(keypair_list)
    print("Checking for keypair: {}".format(keypair_name))
    for key in keypair_list['KeyPairs']:
        if key['KeyName'] == keypair_name:
            print("Keypair exists in AWS")
            return True


def create_keypair(appname, env):

    key_dir = os.path.expanduser('~/.ssh/')
    keypair_name = "aws-east-{0}-{1}".format(appname, env)
    pemfile = os.path.join(key_dir, keypair_name+'.pem')
    exists = check_keypair(keypair_name)

    if not os.path.isfile(pemfile):
        if exists:
            print("The keypair exists in AWS but is missing from Jenkins")
            sys.exit(1)
        proc = sp.Popen(['aws', 'ec2', 'create-key-pair',
                         '--key-name', keypair_name, '--region',
                         'us-east-1'], stdout=sp.PIPE, stderr=sp.PIPE)
        key_out, key_err = proc.communicate()
        key_out = key_out.decode('UTF-8')

        if str(key_out):
            print("Saving private key to pem file")
            key_out = json.loads(key_out)
            keyfile = open(pemfile, 'w')
            keyfile.write(key_out['KeyMaterial'])
            keyfile.close

        if os.path.isfile(pemfile):
            print("Private key exists!")
            return(0)
        else:
            print("No private key found")
            print(key_err.decode('UTF-8'))
            sys.exit(1)


def delete_instances(instance_ids):

    for instance in instance_ids:
        delete_cmd = "knife ec2 server delete {} -y".format(instance)
        delete_cmd = shlex.split(delete_cmd)
        delete_cmd_proc = sp.Popen(delete_cmd)
        cmd_out, cmd_err = delete_cmd_proc.communicate()


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser(description='Wraps knife-ec2 with additional functionality')
    parser.add_argument('--appname', help='Application name should be equal to the github repo name')
    parser.add_argument('--vpc', help='VPC id to create the instance in')
    parser.add_argument('--env', help='Environment to deploy to (preprod or production)')
    parser.add_argument('--tier', help='Tier to deploy instance to (app, public)')
    parser.add_argument('--ec2_size', help='Size of EC2 instance (t2.micro, m3.medium, etc)')
    parser.add_argument('--groups', help='Security group ids to apply to the instance')
    parser.add_argument('--zones', help='List of availability zones to deploy to (us-east-1a,us-east-1c,us-east-1e)')
    parser.add_argument('--iam_profile_id', help='Attachs an IAM role to an ec2 instance')
    parser.add_argument('--chef_client_version', help='Set the version of chef-client when bootstrapped')
    parser.add_argument('--ami_id', help='Set the ec2 image to be used')
    parser.add_argument('--datadog', help='Set to enable datadog integrations')
    parser.set_defaults(iam_profile_id='', chef_client_version='12.17.44',
                        ami_id=None, datadog='false')

    p = parser.parse_args()

    if p.iam_profile_id:
        iam_profile_id = "--iam-profile {}".format(p.iam_profile_id)
        main(p.appname, p.vpc, p.env,
             p.tier, p.ec2_size, p.groups,
             p.zones, iam_profile_id,
             p.chef_client_version,
             p.ami_id, p.datadog)
    else:
        main(p.appname, p.vpc, p.env,
             p.tier, p.ec2_size, p.groups,
             p.zones, p.iam_profile_id,
             p.chef_client_version,
             p.ami_id, p.datadog)
