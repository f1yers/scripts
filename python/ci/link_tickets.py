import re
import subprocess as sp
import json
import requests
import os


"""
Compares unmerged commits in source branch to master
Parses ticket numbers from unmerged commit subjects
Links tickets to supplied JIRA fix version ID

All arguments for this script are required
"""


def main(branch_type, version, version_id, appname):

    ticket_list = list_tickets(branch_type, version, appname)
    if ticket_list:
        print("The following tickets will be associated with version id {}: ".format(version_id) + str(ticket_list))
        link_tickets(ticket_list, version_id)
    else:
        print("No tickets found to link")


def list_tickets(branch_type, version, appname):

    if appname:
        branch = 'origin/{}/{}/{}'.format(appname, branch_type, version)
    else:
        branch = 'origin/{}/{}'.format(branch_type, version)
    commits = sp.check_output(['git', 'log', branch,
                               '^origin/master', '--pretty=format:%s'
                               ]).decode('UTF-8').splitlines()

    print(commits)

    tickets = []
    for msg in commits:
        # Parse the commit message to pull out the JIRA issue ticket
        ticket_regex = r"""
        ([A-Z]+\d?-\d+)+  # Matches unlimited uppercase letters, optional digit,
                          # a hyphen and unlimited digits
        """
        rgx = re.compile(ticket_regex, re.IGNORECASE | re.VERBOSE)
        ticket = rgx.findall(msg)

        if ticket:
            for t in ticket:
                tickets.append(t)

    tickets = sorted(set(tickets))

    return tickets


def link_tickets(ticket_list, version_id):

    headers = {'content-type': 'application/json'}
    auth = (os.environ.get('JIRAUSERNAME', '@@JIRAUSERNAME@@'),
            os.environ.get('JIRAPASSWORD', '@@JIRAPASSWORD@@'))

    update_version_json = {
        "update": {
            "fixVersions": [{
                "add": {
                    "id": ""
                    }
                }]
            }
        }

    update_version_json['update']['fixVersions'][0]['add']['id'] = version_id
    payload = json.dumps(update_version_json)
    print("Payload is: {}".format(payload))

    for ticket in ticket_list:
        url = "https://jira.EXAMPLE.com/rest/api/2/issue/{}".format(ticket)
        print("URL is: {}".format(url))
        try:
            r = requests.put(url, payload, headers=headers, auth=auth)
        except requests.exceptions.HTTPError as e:
            print(e.message)

        if int(r.status_code) > 204:
            print("Failed to link ticket! Error: {0} {1}".format(r.status_code, r.text))

        url = ''


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser(description='Pulls unmerged release branch commits, \
                                                 parses tickets and links to fix version')
    parser.add_argument('--version', help='Release version to find rel branch')
    parser.add_argument('--version_id', help='JIRA fix version ID to link tickets with')
    parser.add_argument('--branch_type', help='The type of branch being compared (release, hotfix..etc)')
    parser.add_argument('--appname', help='If supplied release branch will be evaluated as appname/branch_type/version')
    parser.set_defaults(appname=None)
    p = parser.parse_args()

    main(p.branch_type, p.version, p.version_id, p.appname)
