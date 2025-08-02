import subprocess as sp
import sys
import json
import requests
import re
import os
import boto3
import shutil
from collections import OrderedDict
from importlib.machinery import SourceFileLoader
from datetime import datetime, date, timedelta


"""
Description
-----
In order of operation, this script will do the following:
  1. The next version will be discovered based on the last version released unless an override is supplied (i.e if version 1.0.1, next is 1.0.2)
  2. A release branch is created off of the develop branch, version updated, and develop and release pushed to remote origin
  3. A pull request is opened proposing these changes in the SCM from the release branch into the master branch
  4. JIRA ticket and fix version will be created with a subject "appname - version"
  5. Compares release branch and master branch git log for unmerged commits, parses tickets, and links to fix version.
  6. Finally, all info discovered and created is saved as metadata in json format in s3

Usage
-----
This script should only be ran from a Jenkins build.

usage: create_version.py [-h] [--appname APPNAME] [--apptype APPTYPE]
                         [--project PROJECT] [--release_date RELEASE_DATE]
                         [--branch_type branch_type] [--version VERSION]
                         [--released RELEASED] [--repo_name REPO_NAME]
                         [--git_lab GIT_LAB] [--maven_version MAVEN_VERSION]
                         [--maven_opts MAVEN_OPTS]
                         [--skip_release_start SKIP_RELEASE_START]
                         [--rel_ticket REL_TICKET] [--version_id VERSION_ID]
                         [--pr_link PR_LINK]

Examples
-----
To create a new Java/Maven version:
python3 create_version.py --appname=example-service --apptype=java --project=BCD --repo_name=example-service-repo

To create a new Python version:
python3 create_version.py --appname=example-service --apptype=python --project=JIRA_PROJECT

"""


def main(appname, apptype, jira_project, branch_type, release_date,
         version_override, repo_name, mono_repo, git_lab, maven_version,
         maven_opts, maven_dev_version, skip_release_start,
         skip_link_tickets, rel_ticket, version_id, pr_link):

    print("Application name is: " + appname)
    print("Branch type is: " + branch_type)

    next_version = find_version(appname, apptype, version_override,
                                branch_type, mono_repo)

    if not skip_release_start:
        if apptype.startswith('java'):
            print("Attempting to create Maven Release")
            create_java_version(branch_type, next_version,
                                maven_version, maven_opts,
                                maven_dev_version, apptype)
        elif apptype == 'python':
            print("Attempting to create Python Release")
            # only branch_type, next_version are used
            # required since both call create_branch()
            create_py_version(appname, branch_type, next_version, mono_repo)
        elif apptype == 'node':
            print("Attempting to create Nodejs Release")
            create_node_version(appname, branch_type, next_version, mono_repo)

    if not pr_link:
        if git_lab:
            pr_link = create_glpr(appname, next_version,
                                  repo_name, branch_type, mono_repo)
        else:
            pr_link = create_ghpr(appname, next_version,
                                  repo_name, branch_type, mono_repo)
        print("Pull Request created: " + pr_link)

    if not rel_ticket:
        rel_ticket = create_rel_ticket(appname, next_version)
        print("REL ticket created: " + rel_ticket)

    if not version_id:
        version_id = create_fix_version(appname, next_version, jira_project,
                                        release_date, rel_ticket)
        print("Created fix version {0} for release in project: {1}".format(version_id, jira_project))

    if not skip_link_tickets:
        link_tickets = SourceFileLoader("link_tickets", "/opt/repositories/dev-ops/scripts/ci/v1/link_tickets.py").load_module()
        ticket_list = link_tickets.list_tickets(branch_type, next_version)
        link_tickets.link_tickets(ticket_list, version_id)

    version_link = "https://jira.EXAMPLE.com/projects/{0}/versions/{1}".format(jira_project, version_id)
    update_rel_ticket(rel_ticket, appname, next_version,
                      pr_link, version_link)
    store_version_info(appname, next_version, rel_ticket,
                       version_id, branch_type)


def create_fix_version(appname, next_version, jira_project, release_date, rel_ticket):

    method = 'post'
    url = 'https://jira.EXAMPLE.com/rest/api/2/version'
    version_description = """
    {0} - {1} - {2}
    """.format(rel_ticket, appname, next_version)

    fix_version_json = {
        "name": "",
        "description": "",
        "userReleaseDate": "",
        "project": "",
        "archived": "false",
        "released": "false"
    }

    fix_version_json['name'] = "{0} - {1}".format(appname, next_version)
    fix_version_json['description'] = version_description
    fix_version_json['userReleaseDate'] = release_date
    fix_version_json['project'] = jira_project

    payload = json.dumps(fix_version_json)
    results = make_request(url, method, payload=payload, auth='jira')
    version_id = json.loads(results[0])

    if 'errors' in version_id:
        print('JIRA fix version error')
        print(version_id['errors']['name'])
        print('Rerunning create_version with a new version set might fix this')
        sys.exit(1)

    return version_id['id']


def release_fix_version(version_id):

    method = 'put'
    url = 'https://jira.EXAMPLE.com/rest/api/2/version/{}'.format(version_id)

    fix_version_json = {
        "self": url,
        "id": version_id,
        "released": "true",
        "releaseDate": str(date.today()),
    }

    payload = json.dumps(fix_version_json)
    make_request(url, method, payload=payload, auth='jira')


def create_rel_ticket(appname, next_version):

    method = 'post'
    url = 'https://jira.EXAMPLE.com/rest/api/2/issue'
    ticket_summary = "Releases: {0} - {1}".format(appname, next_version)

    # Build issue payload
    create_ticket_json = {
        "fields": {
            "project": {
                "key": "REL"
            },
            "summary": "",
            "description": "",
            "issuetype": {
                "name": "Automated Release"
            }
        }
    }

    create_ticket_json['fields']['summary'] = ticket_summary

    payload = json.dumps(create_ticket_json)
    results = make_request(url, method, payload=payload, auth='jira')
    rel_ticket = json.loads(results[0])

    return rel_ticket['key']


def update_rel_ticket(rel_ticket, appname, next_version, pr_link, version_link):

    method = 'put'
    url = "https://jira.EXAMPLE.com/rest/api/2/issue/{}".format(rel_ticket)
    ticket_description = """
    {{panel:title=Release Details|borderStyle=dashed|borderColor=#ccc|titleBGColor=#BDBDBD|bgColor=#F2F2F2}}
    _Automated release ticket generated by Jenkins_
    Application: {0}
    Release Version: {1}
    ----
    [*Fix Version*|{2}]
    [*Pull Request*|{3}]
    {{panel}}
    """.format(appname, next_version, version_link, pr_link)

    update_ticket_json = {
        "fields": {
            "description": ""
        }
    }

    update_ticket_json['fields']['description'] = ticket_description
    payload = json.dumps(update_ticket_json)
    make_request(url, method, payload=payload, auth='jira')


def find_version(appname, apptype, version_override, branch_type, mono_repo):

    if not version_override:
        check_branch('master')
        try:
            if apptype.startswith('java'):
                version = sp.check_output(['/usr/local/maven/bin/mvn', '-q', '-Dexec.executable=echo', '-Dexec.args=${project.version}', '--non-recursive', 'org.codehaus.mojo:exec-maven-plugin:1.3.1:exec']).strip().decode('UTF-8')
            if apptype == 'python':
                version = sp.check_output(['python3', './setup.py', '--version']).strip().decode('UTF-8')
            if apptype == 'node':
                with open(os.path.join(os.getcwd(), 'package.json'), 'r') as package_file:
                    data = json.load(package_file, object_pairs_hook=OrderedDict)
                    if mono_repo:
                        version = data['versions'][appname]
                    else:
                        version = data['version']
        except (sp.CalledProcessError, ValueError) as e:
            print('Encountered error parsing version', e.output, e.returncode)
            sys.exit(1)

        print("Current version in master branch is: " + str(version))
        next_version = get_next_version(version, branch_type)
        print("Next release version will be: " + next_version)
    else:
        next_version = version_override
        print("Override version supplied. Next release version will be: " + next_version)

    return next_version


def get_next_version(version, branch_type):

    # Remove the rerun count if exists
    if '-' in version:
        version = version.split("-")[0]

    if 'rc' in version:
        version = version.split("rc")[0]

    version = version.split(".")
    if branch_type == 'hotfix':
        base_version = str(version[0]+"."+version[1]+"."+version[2])
        if len(version) == 4:
            new_hotfix_version = str(int(version[3])+1)
            next_version = base_version+"."+new_hotfix_version
        else:
            next_version = base_version+".1"
    else:
        base_version = str(version[0]+"."+version[1])
        new_patch_version = str(int(version[2])+1)
        next_version = base_version+"."+new_patch_version

    return next_version


def check_branch(expected_branch):

    sp.check_output(['git', 'checkout', expected_branch])
    current_branch = sp.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']
                                     ).strip().decode('UTF-8')

    if current_branch != expected_branch:
        print("Current branch: {0} is not {1}".format(current_branch, expected_branch))
        sys.exit(1)


def create_branch(appname, branch_type, next_version, mono_repo):

    if mono_repo:
        branch_name = "{}/{}/{}".format(appname, branch_type, next_version)
    else:
        branch_name = "{}/{}".format(branch_type, next_version)

    commit_msg = "Updating version for {}".format(branch_name)

    try:
        # Commit version update
        sp.check_output(['git', 'add', '.'])
        sp.check_output(['git', 'commit', '-m', commit_msg])
    except sp.CalledProcessError as e:
        print('Encountered error committing version update', e.output, e.returncode)
        sys.exit(1)

    try:
        # Create new branch and push it up
        sp.check_output(['git', 'checkout', '-b', branch_name])
        sp.check_output(['git', 'push', 'origin', branch_name])
    except sp.CalledProcessError as e:
        print('Encountered error creating branch', e.output, e.returncode)
        sys.exit(1)


def create_node_version(appname, branch_type, next_version, mono_repo):

    if branch_type == 'release':
        check_branch('develop')
    elif branch_type == 'hotfix':
        check_branch('master')

    with open(os.path.join(os.getcwd(), 'package.json'), 'r') as package_file:
        data = json.load(package_file, object_pairs_hook=OrderedDict)

    if mono_repo:
        data['versions'][appname] = next_version
    else:
        data['version'] = next_version

    with open('package.json', 'w') as package_file:
        json.dump(data, package_file, indent=2)

    create_branch(appname, branch_type, next_version, mono_repo)


def create_py_version(appname, branch_type, next_version, mono_repo):

    if branch_type == 'release':
        check_branch('develop')
    elif branch_type == 'hotfix':
        check_branch('master')

    with open(os.path.join(os.getcwd(), 'setup.py'), 'r') as data:
        setup_file = data.read()

    version_regex = "version=\"\d+\.\d+(\.\d+)?(\.\d+)?(rc\d+)?\""
    rgx = re.compile(version_regex, re.IGNORECASE | re.VERBOSE)
    current_version = rgx.search(setup_file)

    replacement = 'version=\"{}\"'.format(next_version)

    if current_version.group(0) == replacement:
        print("Version in setup.py is already what was specified")
        sys.exit(0)

    setup_file = setup_file.replace(current_version.group(0), replacement)

    with open(os.path.join(os.getcwd(), 'setup.py'), 'w') as data:
        data.write(setup_file)

    create_branch(appname, branch_type, next_version, mono_repo)


def create_java_version(branch_type, next_version,
                        maven_version, maven_opts,
                        maven_dev_version, apptype):

    git_bin = 'gitflow'
    if apptype == 'java.system':
        git_bin = 'jgitflow'

    release_version_opt = "-DreleaseVersion={}".format(next_version)

    if branch_type == 'release':
        check_branch('develop')

        if not maven_dev_version:
            maven_dev_version = get_next_version(next_version, branch_type)
        snapshot_version = "{}-SNAPSHOT".format(maven_dev_version)
        dev_version_opt = "-DdevelopmentVersion={}".format(snapshot_version)

        print("Creating release and setting development version to: " + snapshot_version)
        maven_exec = '/usr/local/maven-{0}/bin/mvn'.format(maven_version)
        cmd_list = [maven_exec, release_version_opt, '-DpushRemote=true','-DpushReleases=true', dev_version_opt, '-B', '{}:release-start'.format(git_bin)]
        if maven_opts:
            for opt in maven_opts.split(','):
                cmd_list.append(opt)

    elif branch_type == 'hotfix':
        check_branch('master')

        hotfix_version_opt = "-DhotfixVersion={}".format(next_version)

        print('Creating hotfix release')
        maven_exec = "/usr/local/maven-{0}/bin/mvn".format(maven_version)
        cmd_list = [maven_exec, hotfix_version_opt, '-DpushRemote=true', '-DpushHotfixes=true', '-B', '{}:hotfix-start'.format(git_bin)]
        if maven_opts:
            for opt in maven_opts.split(','):
                cmd_list.append(opt)

    print(cmd_list)
    sys.stdout.flush()
    cmd = sp.Popen(cmd_list)
    cmd.communicate()
    if cmd.returncode != 0:
        print('Encountered error creating version. Return code was: ', cmd.returncode)
        sys.exit(1)
    else:
        print('Version created successfully!')


def create_glpr(appname, next_version, repo_name, branch_type, mono_repo):

    if mono_repo:
        branch_name = "{}/{}/{}".format(appname, branch_type, next_version)
    else:
        branch_name = "{}/{}".format(branch_type, next_version)

    print("Creating pull request from {} branch into master".format(branch_name))

    import gitlab

    gl = gitlab.Gitlab('http://git.EXAMPLE.com', os.environ.get('GITLABTOKEN', '@@GITLABTOKEN@@'))
    project = gl.projects.get(repo_name)

    create_pr_json = {
        "source_branch": "",
        "target_branch": "master",
        "title": ""
    }

    create_pr_json['source_branch'] = branch_name
    create_pr_json['title'] = "{0} - {1}".format(appname, next_version)

    print(create_pr_json)
    gl.project_mergerequests.create(create_pr_json, project_id=project.id)
    pr_link = 'http://git.EXAMPLE.com/{}/merge_requests?f=open'.format(repo_name)

    return pr_link


def create_ghpr(appname, next_version, repo_name, branch_type, mono_repo):

    if mono_repo:
        branch_name = "{}/{}/{}".format(appname, branch_type, next_version)
    else:
        branch_name = "{}/{}".format(branch_type, next_version)

    print("Creating pull request from {} branch into master".format(branch_name))

    method = 'post'
    url = "https://api.github.com/repos/EXAMPLE/{}/pulls".format(repo_name)

    create_pr_json = {
      "title": "",
      "body": "",
      "head": "",
      "base": "master"
    }

    create_pr_json['title'] = "{0} - {1}".format(appname, next_version)
    create_pr_json['head'] = branch_name

    payload = json.dumps(create_pr_json)
    results = make_request(url, method, payload=payload, auth='github')

    if str(results[1]) != '201':
        print("Did not receive OK status after creating PR. Got: " + str(results[1]))
        sys.exit(1)

    pr_link = json.loads(results[0])

    return pr_link['html_url']


def store_version_info(appname, next_version, rel_ticket, version_id, branch_type):

    file_name = "{}.json".format(next_version)
    version_dir = '/tmp/{}'.format(appname)
    if not os.path.exists(version_dir):
        os.makedirs(version_dir)

    fs_file_location = os.path.join(version_dir, file_name)
    s3_file_location = os.path.join(appname, branch_type, file_name)

    store_version_json = {
        "ticket": "",
        "version": "",
        "fixId": "",
        "rerun": []
    }

    store_version_json['ticket'] = rel_ticket
    store_version_json['fixId'] = version_id
    store_version_json['version'] = next_version

    with open(os.path.join(version_dir, file_name), 'w') as outfile:
        json.dump(store_version_json, outfile, sort_keys=True,
                  indent=4, separators=(',', ': '))

    s3c = boto3.client('s3')
    s3c.upload_file(fs_file_location, 'ci-metadata', s3_file_location)
    clean_up_tmp(appname)


def clean_up_tmp(appname):

    version_dir = '/tmp/{}'.format(appname)
    if os.path.exists(version_dir):
        print("Cleaning up local metadata after transfer")
        shutil.rmtree(version_dir)


def make_request(url, method, **kwargs):

    headers = {'content-type': 'application/json'}
    payload = kwargs.get('payload', None)
    auth = kwargs.get('auth', None)

    if auth == 'jira':
        auth = (os.environ.get('JIRAUSERNAME', '@@JIRAUSERNAME@@'),
                os.environ.get('JIRAPASSWORD', '@@JIRAPASSWORD@@'))
    elif auth == 'github':
        auth = (os.environ.get('GITHUBUSERNAME', '@@GITHUBUSERNAME@@'),
                os.environ.get('GITHUBPASSWORD', '@@GITHUBPASSWORD@@'))

    try:
        if method == 'post':
            r = requests.post(url, payload, headers=headers, auth=auth)
        elif method == 'put':
            r = requests.put(url, payload, headers=headers, auth=auth)
        else:
            r = requests.get(url, headers=headers, auth=auth)
    except requests.exceptions.HTTPError as e:
        print("An error occurred when making the request", e.message)

    if r.text is None:
        r.text = 'None'

    return r.text, r.status_code


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser(description='Creates an application release version')
    parser.add_argument('--appname', help='Application name should be equal to the github repo name')
    parser.add_argument('--apptype', help='Defines type of application i.e python, java, node')
    parser.add_argument('--project', help='JIRA project to create a fix version in')
    parser.add_argument('--release_date', help='Expected release date for fix version')
    parser.add_argument('--branch_type', help='Determines the type of branch created')
    parser.add_argument('--version', help='Specify the release version instead of discovering it')
    parser.add_argument('--released', nargs='?', const=True, default=False,
                        help='If set to true to close fix version, supply --version_id')
    parser.add_argument('--repo_name', help='Specify if repo name is different from appname')
    parser.add_argument('--mono_repo', help='Set to True if application exists in a mono repo')
    parser.add_argument('--git_lab', nargs='?', const=True, default=False,
                        help='Defaults to false, set to indicate PR creation on GitLab')
    parser.add_argument('--start_java_release', nargs='?', const=True, default=False,
                        help='Set to true to create a release/PR and exit')
    parser.add_argument('--maven_version', help='Defaults to 3.3.9, override to change the version used to run release start')
    parser.add_argument('--maven_opts', help='Defaults to none, comma delimited to include additional options when starting the release')
    parser.add_argument('--maven_dev_version', help='Specify the development SNAPSHOT version otherwise patch version will be bumped')
    parser.add_argument('--skip_release_start', nargs='?', const=True, default=False,
                        help='Set to true to skip mvn release creation')
    parser.add_argument('--skip_link_tickets', nargs='?', const=True, default=False,
                        help='Set to true to skip link ticket step')
    parser.add_argument('--rel_ticket', help='Skip ticket creation and supply your own REL ticket')
    parser.add_argument('--version_id', help='Skip fix version creation and supply your own ID')
    parser.add_argument('--pr_link', help='Skip pull request creation and supply your own link')
    parser.set_defaults(branch_type='release', version=None, release_date=None,
                        repo_name=None, mono_repo=False, maven_version='3.3.9',
                        maven_opts=None, maven_dev_version=None,
                        rel_ticket=None, version_id=None, pr_link=None)

    p = parser.parse_args()

    if not p.repo_name:
        p.repo_name = p.appname

    if p.released:
        release_fix_version(p.version_id)
        sys.exit(0)

    if p.start_java_release:
        create_java_version(p.branch_type, p.version,
                            p.maven_version, p.maven_opts,
                            p.maven_dev_version, p.apptype)
        if not p.pr_link:
            if p.git_lab:
                pr_link = create_glpr(p.appname, p.version,
                                      p.repo_name, p.branch_type,
                                      p.mono_repo)
            else:
                pr_link = create_ghpr(p.appname, p.version,
                                      p.repo_name, p.branch_type,
                                      p.mono_repo)
        sys.exit(0)

    if not p.release_date:
        date = datetime.strptime(str(datetime.now().date()), '%Y-%m-%d')
        new_date = date + timedelta(days=7)
        p.release_date = new_date.strftime('%m/%d/%Y')

    main(p.appname, p.apptype, p.project,
         p.branch_type, p.release_date, p.version,
         p.repo_name, p.mono_repo, p.git_lab,
         p.maven_version, p.maven_opts, p.maven_dev_version,
         p.skip_release_start, p.skip_link_tickets,
         p.rel_ticket, p.version_id, p.pr_link)
