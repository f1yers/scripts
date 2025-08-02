import ruamel.yaml
import sys
import os

"""
This script will update the image tag in a deployment manifest
Can be used with a multi doc yaml, however ensure that
the deployment doc is LAST one. Example:

kind: Namespace
metadata:....
---
kind: Service
metadata:....
---
kind: Deployment
metadata:....

Also ensure the container spec being updated is the first one
"""


def update_yaml(file, **kwargs):

    tag = kwargs.get('tag', None)
    env = kwargs.get('env', None)

    with open(file+".tmp", 'w') as out_file:
        lines = ''
        with open(file) as in_file:
            # Grabs all documents and their separators
            for line in in_file:
                lines += line
                if line == '---\n':
                    out_file.write(lines)
                    lines = ''

        yaml = ruamel.yaml.YAML()
        yaml.preserve_quotes = True
        data = yaml.load(lines)

        if tag:
            current_image = data['spec']['template']['spec']['containers'][0]['image']
            current_image_prefix = current_image.split(':')[0]
            current_image_tag = current_image.split(':')[1]
            data['spec']['template']['spec']['containers'][0]['image'] = current_image_prefix+":"+tag

            print("Updating deployment image tag from {0} to {1}".format(current_image_tag, tag))

        if env:
            env_key = env.split(":")[0].upper()
            env_value = env.split(":")[1]
            env = data['spec']['template']['spec']['containers'][0]['env']
            for l in env:
                if l['name'] == env_key:
                    print("Replacing: {0} with {1}".format(l['value'], env_value))
                    l['value'] = env_value

        yaml.dump(data, out_file)
    os.rename(file+".tmp", file)


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser(description='Opens k8s deployment yaml and replaces stuff')
    parser.add_argument('--file', help='YAML file relative to cwd')
    parser.add_argument('--tag', help='Supply new tag name to replace')
    parser.add_argument('--env', help='Supply key:value string where value is what will be replaced')
    parser.set_defaults(tag=None, env=None)
    p = parser.parse_args()

    if not p.file:
        sys.exit('You must supply a value for --file')

    update_yaml(p.file, tag=p.tag, env=p.env)
