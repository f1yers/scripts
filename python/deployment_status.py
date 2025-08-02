import subprocess as sp
from sys import exit

"""
This script will determine the status of a deployment in Kubernetes.

If deployment is completed successfully the script will return 0.

If the deployment has failed the script will print failed pod logs
and either undo the rollout or if it is a first time deployment
with no rollout history (no previous replica set), the deployment
will be deleted.

Usage:
----
python3 deployment_status.py [-h] [--timeout TIMEOUT] [--file FILE]
"""


def is_deployment_done(deployment, namespace, timeout, kubeconfig, context):
    status_cmd = ["kubectl", "rollout", "status",
                  "--namespace={}".format(namespace),
                  "deployment/{}".format(deployment),
                  "--timeout={}s".format(timeout),
                  "--kubeconfig={}".format(kubeconfig),
                  "--context={}".format(context)]
    status_process = sp.run(status_cmd)

    if status_process.returncode != 0:
        # print logs
        failed_logs = get_failed_pods_logs(deployment, namespace, kubeconfig, context)
        for log in failed_logs:
            print(log.replace('\\n', '\n'))

        remove_failed_pods(deployment, namespace, kubeconfig, context)

    return status_process.returncode


def remove_failed_pods(deployment, namespace, kubeconfig, context):

    # Try rolling back deployment
    rollback_command = ["kubectl", "rollout", "undo",
                        "--namespace={}".format(namespace),
                        "deployment/{}".format(deployment),
                        "--kubeconfig={}".format(kubeconfig),
                        "--context={}".format(context)]
    rollback_process = sp.run(rollback_command,
                              stdout=sp.PIPE,
                              stderr=sp.STDOUT)
    print(rollback_process.stdout.decode())

    # First time deployment failed so deleted deployment
    if rollback_process.stdout.decode().startswith(
            'error: no rollout history found for deployment'):
        print("Rollback was unsuccessful due to first time deployment, deleting deployment!")
        delete_deployment_cmd = ["kubectl", "delete", "deployment",
                                 "--namespace={}".format(namespace),
                                 "{}".format(deployment),
                                 "--kubeconfig={}".format(kubeconfig),
                                 "--context={}".format(context)]
        sp.run(delete_deployment_cmd)


def get_failed_pods_logs(deployment, namespace, kubeconfig, context):
    logs = []
    get_pods_cmd = ["kubectl", "get", "pods",
                    "--namespace={}".format(namespace),
                    "--selector=app={}".format(deployment),
                    "--no-headers",
                    "--kubeconfig={}".format(kubeconfig),
                    "--context={}".format(context)]
    pods_cmd_process = sp.run(get_pods_cmd,
                              stdout=sp.PIPE,
                              stderr=sp.PIPE)

    pods = []
    # get lines from kubectl get pods command
    for output in pods_cmd_process.stdout.decode().split('\n'):
        if output == '':
            continue
        # if line doesn't contain "Running", find() returns -1
        # also checks if pod status is not ready (0/1)
        if output.find("Running") is -1 or output.find("0/1"):
            print("FAILED POD: " + output.split(' ')[0])
            pods.append(output.split(' ')[0])

    # filter empty entries, then iterate through and get logs
    for pod in list(filter(None, pods)):
        logs_command = ["kubectl", "logs",
                        "--namespace={}".format(namespace),
                        "--kubeconfig={}".format(kubeconfig),
                        "--context={}".format(context),
                        pod]
        logs.append(pod + ': \n')
        logs.append(sp.run(logs_command,
                    stdout=sp.PIPE,
                    stderr=sp.PIPE).stdout.decode())

    return logs


def get_deployment_namespace(file):
    import ruamel.yaml

    lines = ''
    with open(file) as in_file:
        for line in in_file:
            lines += line
            if line == '---\n':
                # deployment type should be last if multidoc yaml
                lines = ''

    yaml = ruamel.yaml.YAML()
    yaml.preserve_quotes = True
    data = yaml.load(lines)

    if 'namespace' not in data['metadata']:
        print('No namespace specified in yaml, using "default"!')
        data['metadata']['namespace'] = 'default'

    return data['metadata']['name'], data['metadata']['namespace']


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser(description='Checks status of K8s deployment and returns results')
    parser.add_argument('--timeout', default='360', help='How long (seconds) to determine if a deployment failed')
    parser.add_argument('--file', help='YAML file relative to cwd')
    parser.add_argument('--kubeconfig', default='/root/.kube/config', help='Location of where kubeconfig resides')
    parser.add_argument('--context', help='K8s cluster to run commands on')
    p = parser.parse_args()

    if not p.file:
        exit('You must supply a value for --file')

    deployment, namespace = get_deployment_namespace(p.file)
    exit(is_deployment_done(deployment, namespace, p.timeout, p.kubeconfig, p.context))
