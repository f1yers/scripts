import jenkins
import time
import sys
import boto3
import json

"""
This script was created to aid jenkins pipelines in running multiple triggered jobs.

Semi-colon separated list of job names:

python3 trigger_builds.py --builds 'Scale-Apps/Portal-APIs;Scale-Apps/Identity'

If parameters are required, specify those first and pipe them into the job requested:

python3 trigger_builds.py --builds 'environment=dev|Scale-Apps/Portal-APIs'
"""


def main(builds, delay, hard_exit_on_failure):

    # convert builds to list
    builds = builds.split(";")
    for job in builds:
        if "|" in job:
            job_name = job.split('|')[1]
            job_params_list = job.split('|')[0].split(',')
            print("This job has parameters that need to be passed!")
            # {'param1': 'test value 1', 'param2': 'test value 2'}
            _json = {}
            for param in job_params_list:
                k, v = param.split('=')
                _json[k] = v

            print("Calling {} with the following parameters: {}".format(job_name, _json))
            server.build_job(job_name, _json)
        else:
            job_name = job
            print("Calling {} without parameters".format(job))
            server.build_job(job_name)

        expected_new_build_number = next_build_number(job_name)
        print("Waiting for {} build #{} to complete successfully.".format(job_name, expected_new_build_number))
        print("Link to job console: {}{}/console".format(server.get_job_info(job_name)['url'], expected_new_build_number))
        while last_successful_build_number(job_name) != expected_new_build_number:
            print("Triggered build still running...")
            if last_failed_build_number(job_name) == expected_new_build_number:
                print("Triggered build failed!")
                if (hard_exit_on_failure):
                    sys.exit(1)
                print("Moving on without throwing a hard error...")
                break

        print("Sleeping for {} seconds".format(delay))
        time.sleep(delay)


def next_build_number(job_name):

    next_build_number = server.get_job_info(job_name)['nextBuildNumber']
    return next_build_number


def last_successful_build_number(job_name):

    last_successful_build_number = server.get_job_info(job_name)['lastSuccessfulBuild']['number']
    return last_successful_build_number


def last_failed_build_number(job_name):

    try:
        last_failed_build_number = server.get_job_info(job_name)['lastFailedBuild']['number']
    except TypeError:
        last_failed_build_number = 0

    return last_failed_build_number


def get_secrets():

    client = boto3.client('secretsmanager')
    secret_response = client.get_secret_value(SecretId="jenkins/jenkins-automation")
    secret_dict = json.loads(secret_response['SecretString'])

    return secret_dict


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser(description='Unpacks values logically to assist a Jenkins job with triggering builds')
    parser.add_argument('--builds', help='Comma separated list of job names, append param list after pipe "|"')
    parser.add_argument('--delay', help='Configure the delay between running multiple jobs', default=5)
    parser.add_argument('--hard_exit_on_failure', help='Hard exit if triggered build fails', default=False)
    p = parser.parse_args()

    secret_dict = get_secrets()
    server = jenkins.Jenkins('https://JENKINS.EXAMPLE.com', username=secret_dict['USER'], password=secret_dict['TOKEN'])

    main(p.builds, p.delay, p.hard_exit_on_failure)
